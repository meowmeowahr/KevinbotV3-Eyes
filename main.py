"""
Kevinbot v3 Eyes
Author: Kevin Ahr
"""

import enum
import json
import threading
import time

import board
import digitalio
import numpy as np
from adafruit_rgb_display import st7789
from PIL import Image, ImageDraw, ImageFont

with open("settings.json", "r", encoding="UTF-8") as f:
    settings = json.load(f)


class States(enum.Enum):
    STATE_LOGO = 0
    STATE_ERROR = 1
    STATE_TV_STATIC = 2
    STATE_EYE_SIMPLE = 3


class Motions(enum.Enum):
    DISABLE = 0
    LEFT_RIGHT = 1
    MANUAL = 2


class MotionSegment(enum.Enum):
    CENTER_FROM_LEFT = 0
    CENTER_FROM_RIGHT = 1
    LEFT = 2
    RIGHT = 3


class StateWatcher:
    def __init__(self):
        self._state = States(settings["states"]["page"])

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, s):
        self._state = s

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

image = Image.new("RGB", (width, height))
draw = ImageDraw.Draw(image)


def create_logo():
    previous_state = state_watcher.state
    state_watcher.state = States.STATE_LOGO
    image = Image.open(settings["images"]["logo"])
    disp.image(image)
    state_watcher.state = previous_state


def error_periodic(error=0):
    global image, draw, last_redraw, error_border_visible

    if last_redraw + settings["error_format"]["flash_speed"] < time.time():
        error_border_visible = not error_border_visible
        if error_border_visible:
            draw.rectangle((0, 0, width, height), fill=settings["error_format"]["color"])
        else:
            draw.rectangle((0, 0, width, height), fill=settings["error_format"]["bg_color"])

        draw.rectangle(
            (settings["error_format"]["border"],
            settings["error_format"]["border"],
            width - settings["error_format"]["border"] - 1,
            height - settings["error_format"]["border"] - 1),
            fill=settings["error_format"]["bg_color"]
        )

        font = ImageFont.truetype(settings["error_format"]["font"],
                                  settings["error_format"]["font_size"])
        (font_width, font_height) = font.getsize(settings["error_format"]["text"].format(error))
        
        draw.text(
            (width // 2 - font_width // 2, height // 2 - font_height // 2),
            settings["error_format"]["text"].format(error),
            font=font,
            fill=settings["error_format"]["color"]
        )

        disp.image(image)
        last_redraw = time.time()


def tv_static_periodic():
    global image, draw, last_redraw

    if last_redraw + 0.1 < time.time():
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


def eye_simple_style():
    global image, draw, last_redraw

    if last_redraw + 0.05 < time.time():
        draw.rectangle((0, 0, width, height), fill=settings["skins"]["simple"]["bg_color"])
        draw.ellipse((eye_x - settings["skins"]["simple"]["iris_size"] // 2,
                      eye_y - settings["skins"]["simple"]["iris_size"] // 2,
                      eye_x + settings["skins"]["simple"]["iris_size"] // 2,
                      eye_y + settings["skins"]["simple"]["iris_size"] // 2),
                      fill=settings["skins"]["simple"]["iris_color"])

        draw.ellipse((eye_x - settings["skins"]["simple"]["pupil_size"] // 2,
                      eye_y - settings["skins"]["simple"]["pupil_size"] // 2,
                      eye_x + settings["skins"]["simple"]["pupil_size"] // 2,
                      eye_y + settings["skins"]["simple"]["pupil_size"] // 2),
                      fill=settings["skins"]["simple"]["pupil_color"])


        disp.image(image)
        last_redraw = time.time()

def cubic_in_out(t):
    if t < 0.5:
        return 4 * t ** 3
    else:
        return 1 - (-2 * t + 2) ** 3 / 2

def eye_motion():
    global motion, eye_x
    motion_segment = MotionSegment.RIGHT
    while True:
        if motion == Motions.LEFT_RIGHT:
            if motion_segment == MotionSegment.LEFT:
                target_point = (settings["skins"]["simple"]["left_point"])
            elif motion_segment == MotionSegment.RIGHT:
                target_point = (settings["skins"]["simple"]["right_point"])
            
            start_x = eye_x
            end_x = target_point[0]
            num_steps = 200

            for step in range(num_steps + 1):
                t = step / num_steps
                easing_t = cubic_in_out(t)

                x = start_x + (end_x - start_x) * easing_t
                eye_x = x

                if not motion == Motions.LEFT_RIGHT:
                    break

                time.sleep(0.01)

            if eye_x == target_point[0]:
                if motion_segment == MotionSegment.LEFT:
                    motion_segment = MotionSegment.RIGHT
                elif motion_segment == MotionSegment.RIGHT:
                    motion_segment = MotionSegment.LEFT


def main_loop():
    while True:
        if state_watcher.state == States.STATE_ERROR:
            error_periodic(settings["states"]["error"])
        elif state_watcher.state == States.STATE_TV_STATIC:
            tv_static_periodic()
        elif state_watcher.state == States.STATE_EYE_SIMPLE:
            eye_simple_style()
        time.sleep(0.001)


if __name__ == "__main__":
    create_logo()
    time.sleep(settings["images"]["logo_time"])

    motion_thread = threading.Thread(target=eye_motion, daemon=True)
    motion_thread.start()

    main_loop()
