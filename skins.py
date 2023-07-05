"""
Skins for Kevinbot v3 Eyes
Author: Kevin Ahr
"""

import time

import numpy as np
from adafruit_rgb_display.rgb import Display
from PIL import Image, ImageDraw

import utils

realistic_iris = Image.open("iris.png")
aluminum = Image.open("aluminum.png")


def eye_simple_style(display: Display,
                     last_redraw,
                     settings,
                     pos: iter=(120,120),
                     size: iter=(240, 240)):
    """
    Simple Eye Skin
    Kevinbot v2 Style Eye
    """
    eye_x, eye_y = pos

    if last_redraw + 0.05 < time.time():
        image = Image.new("RGB", (size[0], size[1]))
        draw = ImageDraw.Draw(image)

        draw.rectangle((0, 0, size[0], size[1]),
                       fill=settings["skins"]["simple"]["bg_color"])
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

        display.image(image)
        last_redraw = time.time()


def eye_metallic_style(display: Display,
                       last_redraw,
                       settings,
                       pos: iter=(120,120),
                       size: iter=(240, 240)):
    """
    Metalic Eye Skin
    "Aluminum" background with realistic eye
    """
    eye_x, eye_y = pos

    if last_redraw + 0.05 < time.time():
        image = Image.new("RGB", (size[0], size[1]))
        draw = ImageDraw.Draw(image)

        draw.rectangle((0, 0, size[0], size[1]),
                       fill=settings["skins"]["realistic"]["bg_color"])

        iris = realistic_iris.resize(
            (settings["skins"]["realistic"]["iris_size"],
             settings["skins"]["realistic"]["iris_size"]))
        iris_array = np.array(iris)
        shifted_iris = Image.fromarray(
            utils.shift_hue(
                iris_array,
                settings["skins"]["realistic"]["tint"]),
            'RGBA')

        image.paste(aluminum.resize((size[0], size[1])), (0, 0))

        image.paste(shifted_iris, (int(eye_x - iris.width // 2),
                                   int(eye_y - iris.height // 2)), iris)

        display.image(image)
        last_redraw = time.time()
