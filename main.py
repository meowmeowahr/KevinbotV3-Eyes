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
import busio
import numpy as np
from adafruit_rgb_display import st7789
from gpiozero import PWMLED, Device
from gpiozero.pins.rpigpio import RPiGPIOFactory
from PIL import Image, ImageDraw, ImageFont
import serial

from assets import AssetManager
import skins
import utils

# Change the default pin factory for gpiozero
# Since there are some issues with the default lgpio factory, I am switching back to the RPi.GPIO factory
Device.pin_factory = RPiGPIOFactory()


class VisualPage(utils.ExtendedIntEnum):
    """
    Page excluding special pages of display
    """

    STATE_TV_STATIC = 0
    STATE_EYE_SIMPLE = 1
    STATE_EYE_METAL = 2
    STATE_EYE_NEON = 3


class State(enum.Enum):
    """
    State of display
    """

    LOGO = 0
    WAIT = 1
    ERORR = 2
    HOME = 3


class Motions(enum.Enum):
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


class RobotEyes:
    def __init__(self):
        self.settings = {}
        with open("settings.json", "r", encoding="UTF-8") as f:
            self.settings = json.load(f)

        self.assets = AssetManager()
        self.last_redraw = time.time()
        self.previous_time = time.time()
        self.error_border_visible = True
        self.ser = serial.Serial(
            self.settings["comms"]["port"], self.settings["comms"]["baud"]
        )

        self.visual_page = utils.clamp(
            self.settings["states"]["page"], 0, len(VisualPage.list())
        )
        self.state = State.LOGO
        self.motion = Motions(self.settings["states"]["motion"])

        self.eye_x = 120
        self.eye_y = 120

        # Init display
        self.display_1_cs = digitalio.DigitalInOut(board.CE0)
        self.display_1_dc = digitalio.DigitalInOut(board.D25)
        self.display_1_rt = digitalio.DigitalInOut(board.D24)

        self.display_2_cs = digitalio.DigitalInOut(board.CE1)
        self.display_2_dc = digitalio.DigitalInOut(board.D23)
        self.display_2_rt = digitalio.DigitalInOut(board.D22)

        self.bl_pin = 16

        self.spi_0 = busio.SPI(clock=board.SCK, MOSI=board.MOSI)
        self.spi_1 = busio.SPI(clock=board.SCK_1, MOSI=board.MOSI_1)

        self.backlight = PWMLED(self.bl_pin)
        self.backlight.value = self.settings["display"]["backlight"] / 100

        self.display_0 = st7789.ST7789(
            self.spi_0,
            height=240,
            y_offset=80,
            rotation=180,
            cs=self.display_1_cs,
            dc=self.display_1_dc,
            rst=self.display_1_rt,
            baudrate=self.settings["display"]["speed"],
        )

        self.display_1 = st7789.ST7789(
            self.spi_1,
            height=240,
            y_offset=80,
            rotation=180,
            cs=self.display_2_cs,
            dc=self.display_2_dc,
            rst=self.display_2_rt,
            baudrate=self.settings["display"]["speed"],
        )

        # Detect if widht and height need to be swapped
        if self.display_0.rotation % 180 == 90:
            self.height = self.display_0.width
            self.width = self.display_0.height
        else:
            self.width = self.display_0.width
            self.height = self.display_0.height

    def run(self):
        serial_thread = threading.Thread(target=self.serial_loop, daemon=True)
        serial_thread.start()

        motion_thread = threading.Thread(target=self.eye_motion, daemon=True)
        motion_thread.start()

        self.main_loop()

    def save_settings(self):
        """
        Save settings.json
        """
        with open("settings.json", "w", encoding="UTF-8") as file:
            json.dump(self.settings, file, indent=2)

    def create_logo(self):
        """
        Show Kevinbot v3 Logo on screen
        """
        image = self.assets.logo
        self.display_0.image(image)
        self.display_1.image(image)

    def create_loading(self):
        """
        Show loading page while main system connects
        """
        image = Image.new("RGB", (self.width, self.height))
        draw = ImageDraw.Draw(image)

        draw.rectangle(
            (0, 0, self.width, self.height),
            fill=self.settings["loading_format"]["color"],
        )

        draw.rectangle(
            (
                self.settings["loading_format"]["border"],
                self.settings["loading_format"]["border"],
                self.width - self.settings["loading_format"]["border"] - 1,
                self.height - self.settings["loading_format"]["border"] - 1,
            ),
            fill=self.settings["loading_format"]["bg_color"],
        )

        font = ImageFont.truetype(
            self.settings["loading_format"]["font"],
            self.settings["loading_format"]["font_size"],
        )
        (_, _, font_width, font_height) = font.getbbox(
            self.settings["loading_format"]["text"]
        )

        draw.text(
            (self.width // 2 - font_width // 2, self.height // 2 - font_height // 2),
            self.settings["loading_format"]["text"].format("error"),
            font=font,
            fill=self.settings["loading_format"]["color"],
        )

        self.display_0.image(image)
        self.display_1.image(image)

    def error_periodic(self, error=0):
        global last_redraw, error_border_visible

        if last_redraw + self.settings["error_format"]["flash_speed"] < time.time():
            image = Image.new("RGB", (self.width, self.height))
            draw = ImageDraw.Draw(image)

            error_border_visible = not error_border_visible
            if error_border_visible:
                draw.rectangle(
                    (0, 0, self.width, self.height),
                    fill=self.settings["error_format"]["color"],
                )
            else:
                draw.rectangle(
                    (0, 0, self.width, self.height),
                    fill=self.settings["error_format"]["bg_color"],
                )

            draw.rectangle(
                (
                    self.settings["error_format"]["border"],
                    self.settings["error_format"]["border"],
                    self.width - self.settings["error_format"]["border"] - 1,
                    self.height - self.settings["error_format"]["border"] - 1,
                ),
                fill=self.settings["error_format"]["bg_color"],
            )

            font = ImageFont.truetype(
                self.settings["error_format"]["font"],
                self.settings["error_format"]["font_size"],
            )
            (_, _, font_width, font_height) = font.getbbox(
                self.settings["error_format"]["text"].format(error)
            )

            draw.text(
                (
                    self.width // 2 - font_width // 2,
                    self.height // 2 - font_height // 2,
                ),
                self.settings["error_format"]["text"].format(error),
                font=font,
                fill=self.settings["error_format"]["color"],
            )

            self.display_0.image(image)
            self.display_1.image(image)
            last_redraw = time.time()

    def tv_static_periodic(self):
        global last_redraw

        if self.last_redraw + 0.1 < time.time():
            image = Image.new("RGB", (self.width, self.height))

            random_pixels = np.random.randint(
                0,
                256,
                size=(self.display_0.width // 2, self.display_0.height // 2, 3),
                dtype=np.uint8,
            )

            # Repeat each pixel to form 2x2 blocks
            static = np.repeat(np.repeat(random_pixels, 2, axis=0), 2, axis=1)

            # Create a PIL Image from the numpy array
            image = Image.fromarray(static)

            self.display_0.image(image)
            self.display_1.image(image)
            last_redraw = time.time()

    def eye_motion(self):
        motion_segment = MotionSegment.RIGHT
        step = 0
        while True:
            if self.motion == Motions.LEFT_RIGHT:
                num_steps = utils.map_range(
                    self.settings["motions"]["speed"], 0, 100, 620, 20
                )

                self.eye_x = utils.map_range(
                    utils.cubic_in_out(utils.reflect_mod(step, 1)),
                    0,
                    1,
                    self.settings["motions"]["left_point"][0],
                    self.settings["motions"]["right_point"][0],
                )
                self.eye_y = self.height // 2

                time.sleep(0.01)
                num_steps = utils.map_range(
                    self.settings["motions"]["speed"], 0, 100, 620, 20
                )
                step += 2 / num_steps

            elif self.motion == Motions.JUMP:
                num_steps = utils.map_range(
                    self.settings["motions"]["speed"], 0, 100, 620, 20
                )

                self.eye_x = utils.map_range(
                    utils.step_jump_curve(utils.reflect_mod(step, 1)),
                    0,
                    1,
                    self.settings["motions"]["left_point"][0],
                    self.settings["motions"]["right_point"][0],
                )
                self.eye_y = self.height // 2

                time.sleep(0.01)
                num_steps = utils.map_range(
                    self.settings["motions"]["speed"], 0, 100, 620, 20
                )
                step += 2 / num_steps

            elif self.motion == Motions.MANUAL:
                self.eye_x, self.eye_y = self.settings["motions"]["pos"]
                time.sleep(0.01)

            else:
                time.sleep(0.05)

    def request_handshake(self):
        """
        Send a handshake request to the core
        """
        self.ser.write(b"handshake.request\n")

    def main_loop(self):
        """
        Display loop
        Update displays with skin
        """
        start_time = time.time()
        self.request_handshake()
        last_handshake_request = time.time()
        while True:
            if self.state == State.LOGO:
                self.create_logo()
                if time.time() - start_time > self.settings["logo_format"]["logo_time"]:
                    self.state = State.WAIT
            elif self.state == State.WAIT:
                self.create_loading()
                if time.time() - last_handshake_request > 1:
                    self.request_handshake()
                    last_handshake_request = time.time()
            elif self.state == State.ERORR:
                self.error_periodic(self.settings["states"]["error"])
            elif self.state == State.HOME:
                if self.visual_page == VisualPage.STATE_TV_STATIC:
                    self.tv_static_periodic()
                elif self.visual_page == VisualPage.STATE_EYE_SIMPLE:
                    skins.eye_simple_style(
                        (self.display_0, self.display_1),
                        self.last_redraw,
                        self.settings,
                        (self.eye_x, self.eye_y),
                        (self.width, self.height),
                    )
                elif self.visual_page == VisualPage.STATE_EYE_METAL:
                    skins.eye_metallic_style(
                        (self.display_0, self.display_1),
                        self.last_redraw,
                        self.settings,
                        (self.eye_x, self.eye_y),
                        (self.width, self.height),
                    )
                elif self.visual_page == VisualPage.STATE_EYE_NEON:
                    skins.eye_neon_style(
                        (self.display_0, self.display_1),
                        self.last_redraw,
                        self.settings,
                        (self.eye_x, self.eye_y),
                        (self.width, self.height),
                    )
            time.sleep(0.022)  # 45fps

    def serial_loop(self):
        # send settings on start
        settings_copy = copy.deepcopy(self.settings)
        settings_copy.pop("error_format")
        utils.send_data(settings_copy, self.ser, "eye_settings.")

        while True:
            data = self.ser.readline().decode("UTF-8")
            pair = data.strip("\r\n").split("=", 1)
            print(pair)
            if pair[0] == "handshake.complete":
                self.state = State.HOME
            elif len(pair) == 2:
                if pair[0] == "setState":
                    if pair[1].isdigit():
                        self.settings["states"]["page"] = utils.clamp(
                            int(pair[1]), 1, len(VisualPage.list())
                        )
                        self.visual_page = VisualPage(self.settings["states"]["page"])
                        self.save_settings()
                        previous_time = time.time()
                elif pair[0] == "setError":
                    if pair[1].isdigit():
                        self.settings["states"]["error"] = int(pair[1])
                        self.save_settings()
                elif pair[0] == "setSkinOption":
                    option_pairs = pair[1].split(":")
                    if len(option_pairs) == 3:
                        if option_pairs[2].isdigit():
                            value = int(option_pairs[2])
                        else:
                            value = option_pairs[2]
                        if not option_pairs[0] in self.settings["skins"]:
                            logging.warning("Skin %s does not exist", option_pairs[0])
                            continue

                        if (
                            not option_pairs[1]
                            in self.settings["skins"][option_pairs[0]]
                        ):
                            logging.warning(
                                "Option %s for %s does not exist",
                                option_pairs[1],
                                option_pairs[0],
                            )
                            continue

                        if type(
                            self.settings["skins"][option_pairs[0]][option_pairs[1]]
                        ) in (
                            list,
                            tuple,
                        ):
                            logging.warning("Cannot change a list or tuple object")
                        else:
                            self.settings["skins"][option_pairs[0]][
                                option_pairs[1]
                            ] = value
                            self.save_settings()
                    else:
                        logging.warning("Expected 3 values, got %s", len(option_pairs))
                elif pair[0] == "setMotion":
                    if pair[1].isdigit():
                        if int(pair[1]) in range(len(Motions.list())):
                            self.settings["states"]["motion"] = int(pair[1])
                            self.motion = Motions(int(pair[1]))
                            self.save_settings()
                    else:
                        logging.warning("Expected digits, got %s", pair[1])
                elif pair[0] == "getSettings":
                    settings_copy = copy.deepcopy(self.settings)
                    settings_copy.pop("error_format")
                    utils.send_data(settings_copy, self.ser, "eyeSettings.")
                elif pair[0] == "setBacklight":
                    if pair[1].isdigit():
                        self.backlight.value = int(pair[1]) / 100
                        self.settings["display"]["backlight"] = int(pair[1])
                        self.save_settings()
                elif pair[0] == "setSpeed":
                    if pair[1].isdigit():
                        self.settings["motions"]["speed"] = int(pair[1])
                        self.save_settings()
                elif pair[0] == "setPosition":
                    coord = pair[1].split(",", 1)
                    self.settings["motions"]["pos"] = [int(coord[0]), int(coord[1])]
                    self.save_settings()

            else:
                logging.warning("Expected 2 pairs, got %s", len(pair))


if __name__ == "__main__":
    logging.basicConfig()
    eyes = RobotEyes()
    eyes.run()
