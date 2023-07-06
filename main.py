"""
Kevinbot v3 Eyes
Author: Kevin Ahr
"""

import enum
import json
import threading
import logging
import time
import copy

import board
import digitalio
import numpy as np
from adafruit_rgb_display import st7789
from PIL import Image, ImageDraw, ImageFont
import serial

import skins
import utils


SERIAL_PORT = "/dev/ttyS0"
SERIAL_BAUD = 115200

with open("settings.json", "r", encoding="UTF-8") as f:
    settings = json.load(f)


def clamp(val, minn, maxn):
    """
    Clamp value to min/max
    """
    return max(min(maxn, val), minn)


class ExtendedEnum(enum.Enum):
    """
    Extended Enum Class
    Adds list() function
    """
    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))


class States(ExtendedEnum):
    """
    States of display
    """
    STATE_LOGO = 0
    STATE_ERROR = 1
    STATE_TV_STATIC = 2
    STATE_EYE_SIMPLE = 3
    STATE_EYE_METAL = 4
    STATE_EYE_NEON = 5


class Motions(ExtendedEnum):
    """
    Animations for display
    """
    DISABLE = 0
    LEFT_RIGHT = 1
    JUMP = 2
    MANUAL = 3


class MotionSegment(enum.Enum):
    """
    Segments of animation
    """
    CENTER_FROM_LEFT = 0
    CENTER_FROM_RIGHT = 1
    LEFT = 2
    RIGHT = 3


class StateWatcher:
    """
    Watches state of display
    """

    def __init__(self):
        self._state = States(
            clamp(
                settings["states"]["page"], 1, len(
                    States.list())))

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, val):
        self._state = val


last_redraw = time.time()
error_border_visible = True
state_watcher = StateWatcher()
motion = Motions(settings["states"]["motion"])

eye_x = 120
eye_y = 120

# Init display
cs_pin = digitalio.DigitalInOut(board.CE0)
dc_pin = digitalio.DigitalInOut(board.D25)
reset_pin = digitalio.DigitalInOut(board.D24)

spi = board.SPI()

disp = st7789.ST7789(
    spi,
    height=240,
    y_offset=80,
    rotation=180,
    cs=cs_pin,
    dc=dc_pin,
    rst=reset_pin,
    baudrate=settings["display"]["speed"],
)

if disp.rotation % 180 == 90:
    height = disp.width  # we swap height/width to rotate it to landscape!
    width = disp.height
else:
    width = disp.width  # we swap height/width to rotate it to landscape!
    height = disp.height


def save_settings():
    """
    Save settings.json
    """
    with open('settings.json', 'w', encoding="UTF-8") as file:
        json.dump(settings, file, indent=2)


def create_logo():
    """
    Show Kevinbot v3 Logo on screen
    """
    previous_state = state_watcher.state
    state_watcher.state = States.STATE_LOGO
    image = Image.open(settings["images"]["logo"])
    disp.image(image)
    state_watcher.state = previous_state


def error_periodic(error=0):
    global last_redraw, error_border_visible

    if last_redraw + settings["error_format"]["flash_speed"] < time.time():
        image = Image.new("RGB", (width, height))
        draw = ImageDraw.Draw(image)

        error_border_visible = not error_border_visible
        if error_border_visible:
            draw.rectangle((0, 0, width, height),
                           fill=settings["error_format"]["color"])
        else:
            draw.rectangle((0, 0, width, height),
                           fill=settings["error_format"]["bg_color"])

        draw.rectangle(
            (settings["error_format"]["border"],
             settings["error_format"]["border"],
             width - settings["error_format"]["border"] - 1,
             height - settings["error_format"]["border"] - 1),
            fill=settings["error_format"]["bg_color"]
        )

        font = ImageFont.truetype(settings["error_format"]["font"],
                                  settings["error_format"]["font_size"])
        (font_width, font_height) = font.getsize(
            settings["error_format"]["text"].format(error))

        draw.text(
            (width // 2 - font_width // 2, height // 2 - font_height // 2),
            settings["error_format"]["text"].format(error),
            font=font,
            fill=settings["error_format"]["color"]
        )

        disp.image(image)
        last_redraw = time.time()


def tv_static_periodic():
    global last_redraw

    if last_redraw + 0.1 < time.time():
        image = Image.new("RGB", (width, height))

        random_pixels = np.random.randint(
            0, 256,
            size=(disp.width // 2, disp.height // 2, 3),
            dtype=np.uint8)

        # Repeat each pixel to form 2x2 blocks
        static = np.repeat(np.repeat(random_pixels, 2, axis=0), 2, axis=1)

        # Create a PIL Image from the numpy array
        image = Image.fromarray(static)

        disp.image(image)
        last_redraw = time.time()


def cubic_in_out(t):
    """
    CubicInOut Easing Curve
    """
    if t < 0.5:
        return 4 * t ** 3
    else:
        return 1 - (-2 * t + 2) ** 3 / 2


def eye_motion():
    global eye_x
    motion_segment = MotionSegment.RIGHT
    previous_time = time.time()
    while True:
        if motion == Motions.LEFT_RIGHT:
            if motion_segment == MotionSegment.LEFT:
                target_point = settings["motions"]["left_point"]
            elif motion_segment == MotionSegment.RIGHT:
                target_point = settings["motions"]["right_point"]
            else:
                target_point = settings["motions"]["center_point"]

            start_x = eye_x
            end_x = target_point[0]
            num_steps = 200

            for step in range(num_steps + 1):
                t = step / num_steps
                easing_t = cubic_in_out(t)

                x = start_x + (end_x - start_x) * easing_t
                eye_x = x

                if motion != Motions.LEFT_RIGHT:
                    break

                time.sleep(0.01)

            if eye_x == target_point[0]:
                if motion_segment == MotionSegment.LEFT:
                    motion_segment = MotionSegment.RIGHT
                elif motion_segment == MotionSegment.RIGHT:
                    motion_segment = MotionSegment.LEFT
        if motion == Motions.JUMP:
            current_time = time.time()
            elapsed_time = current_time - previous_time

            if elapsed_time >= settings["motions"]["jump_time"]:
                previous_time = current_time

                if motion_segment == MotionSegment.LEFT:
                    target_point = settings["motions"]["left_point"]
                elif motion_segment == MotionSegment.RIGHT:
                    target_point = settings["motions"]["right_point"]
                else:
                    target_point = settings["motions"]["center_point"]

                start_x = eye_x
                end_x = target_point[0]
                eye_x = end_x

                if eye_x == target_point[0]:
                    if motion_segment == MotionSegment.LEFT:
                        motion_segment = MotionSegment.CENTER_FROM_LEFT
                    elif motion_segment == MotionSegment.RIGHT:
                        motion_segment = MotionSegment.CENTER_FROM_RIGHT
                    elif motion_segment == MotionSegment.CENTER_FROM_LEFT:
                        motion_segment = MotionSegment.RIGHT
                    elif motion_segment == MotionSegment.CENTER_FROM_RIGHT:
                        motion_segment = MotionSegment.LEFT

            else:
                time.sleep(0.05)


def main_loop():
    while True:
        if state_watcher.state == States.STATE_ERROR:
            error_periodic(settings["states"]["error"])
        elif state_watcher.state == States.STATE_TV_STATIC:
            tv_static_periodic()
        elif state_watcher.state == States.STATE_EYE_SIMPLE:
            skins.eye_simple_style(
                disp, last_redraw, settings, (eye_x, eye_y), (width, height))
        elif state_watcher.state == States.STATE_EYE_METAL:
            skins.eye_metallic_style(
                disp, last_redraw, settings, (eye_x, eye_y), (width, height))
        elif state_watcher.state == States.STATE_EYE_NEON:
            skins.eye_neon_style(
                disp, last_redraw, settings, (eye_x, eye_y), (width, height))
        time.sleep(0.001)


def serial_loop():
    global motion

    while True:
        data = ser.readline().decode("UTF-8")
        pair = data.strip("\r\n").split("=")
        print(pair)
        if len(pair) == 2:
            if pair[0] == "set_state":
                if pair[1].isdigit():
                    settings["states"]["page"] = clamp(
                        int(pair[1]), 1, len(States.list()))
                    state_watcher.state = States(settings["states"]["page"])
                    save_settings()
            elif pair[0] == "set_error":
                if pair[1].isdigit():
                    settings["states"]["error"] = int(pair[1])
                    save_settings()
            elif pair[0] == "set_skin_option":
                option_pairs = pair[1].split(":")
                if len(option_pairs) == 3:
                    if option_pairs[2].isdigit():
                        value = int(option_pairs[2])
                    else:
                        value = option_pairs[2]
                    if not option_pairs[0] in settings["skins"]:
                        logging.warning(
                            "Skin %s does not exist", option_pairs[0])
                        continue

                    if not option_pairs[1] in settings["skins"][option_pairs[0]]:
                        logging.warning(
                            "Option %s for %s does not exist",
                            option_pairs[1],
                            option_pairs[0])
                        continue

                    if type(settings["skins"][option_pairs[0]]
                            [option_pairs[1]]) in (list, tuple):
                        logging.warning(
                            "Cannot change a list or tuple object")
                    else:
                        settings["skins"][option_pairs[0]
                                          ][option_pairs[1]] = value
                        save_settings()
                else:
                    logging.warning(
                        "Expected 3 values, got %s",
                        len(option_pairs))
            elif pair[0] == "set_motion":
                if pair[1].isdigit():
                    if int(pair[1]) in range(len(Motions.list())):
                        settings["states"]["motion"] = int(pair[1])
                        motion = Motions(int(pair[1]))
                        save_settings()
                else:
                    logging.warning("Expected digits, got %s", pair[1])
            elif pair[0] == "get_settings":
                settings_copy = copy.deepcopy(settings)
                settings_copy.pop("error_format")
                utils.send_data(settings_copy, ser, "eye_settings.")
        else:
            logging.warning("Expected 2 pairs, got %s", len(pair))


if __name__ == "__main__":
    logging.basicConfig()
    ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD)

    create_logo()
    time.sleep(settings["images"]["logo_time"])

    motion_thread = threading.Thread(target=eye_motion, daemon=True)
    motion_thread.start()

    serial_thread = threading.Thread(target=serial_loop, daemon=True)
    serial_thread.start()

    main_loop()
