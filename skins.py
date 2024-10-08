"""
Skins for Kevinbot v3 Eyes
Author: Kevin Ahr
"""

import os
import time

from adafruit_rgb_display.rgb import Display
from PIL import Image, ImageDraw

from assets import AssetManager
import utils


assets = AssetManager()


def eye_simple_style(
    displays: tuple[Display],
    last_redraw,
    settings,
    pos: iter = (120, 120),
    size: iter = (240, 240),
):
    """
    Simple Eye Skin
    Kevinbot v2 Style Eye
    """
    eye_x, eye_y = pos

    if last_redraw + 0.05 < time.time():
        image = Image.new("RGB", (size[0], size[1]))
        draw = ImageDraw.Draw(image)

        draw.rectangle(
            (0, 0, size[0], size[1]), fill=settings["skins"]["simple"]["bg_color"]
        )
        draw.ellipse(
            (
                eye_x - settings["skins"]["simple"]["iris_size"] // 2,
                eye_y - settings["skins"]["simple"]["iris_size"] // 2,
                eye_x + settings["skins"]["simple"]["iris_size"] // 2,
                eye_y + settings["skins"]["simple"]["iris_size"] // 2,
            ),
            fill=settings["skins"]["simple"]["iris_color"],
        )

        draw.ellipse(
            (
                eye_x - settings["skins"]["simple"]["pupil_size"] // 2,
                eye_y - settings["skins"]["simple"]["pupil_size"] // 2,
                eye_x + settings["skins"]["simple"]["pupil_size"] // 2,
                eye_y + settings["skins"]["simple"]["pupil_size"] // 2,
            ),
            fill=settings["skins"]["simple"]["pupil_color"],
        )

        for disp in displays:
            disp.image(image)
        last_redraw = time.time()


def eye_metallic_style(
    displays: tuple[Display],
    last_redraw,
    settings,
    pos: iter = (120, 120),
    size: iter = (240, 240),
):
    """
    Metalic Eye Skin
    "Aluminum" background with realistic eye
    """
    eye_x, eye_y = pos

    if last_redraw + 0.05 < time.time():
        image = Image.new("RGB", (size[0], size[1]))
        draw = ImageDraw.Draw(image)

        draw.rectangle(
            (0, 0, size[0], size[1]), fill=settings["skins"]["metal"]["bg_color"]
        )

        iris = assets.iris.resize(
            (
                settings["skins"]["metal"]["iris_size"],
                settings["skins"]["metal"]["iris_size"],
            )
        )
        shifted_iris = utils.shift_hue(iris, settings["skins"]["metal"]["tint"])

        image.paste(assets.aluminum.resize((size[0], size[1])), (0, 0))

        image.paste(
            shifted_iris,
            (int(eye_x - iris.width // 2), int(eye_y - iris.height // 2)),
            iris,
        )

        for disp in displays:
            disp.image(image)
        last_redraw = time.time()


def eye_neon_style(
    displays: tuple[Display],
    last_redraw,
    settings,
    pos: iter = (120, 120),
    size: iter = (240, 240),
):
    """
    Neon Eye Skin
    """
    eye_x, eye_y = pos

    if last_redraw + 0.05 < time.time():
        image = Image.new("RGB", (size[0], size[1]))
        draw = ImageDraw.Draw(image)

        draw.rectangle(
            (0, 0, size[0], size[1]), fill=settings["skins"]["neon"]["bg_color"]
        )

        iris_image = Image.open(
            os.path.join("assets", "neon", settings["skins"]["neon"]["style"])
        )
        iris = iris_image.resize(
            (
                settings["skins"]["neon"]["iris_size"],
                settings["skins"]["neon"]["iris_size"],
            ),
            Image.Resampling.LANCZOS,
        )

        motion_progress = utils.clamp(
            utils.map_range(
                eye_x,
                settings["motions"]["left_point"][0],
                settings["motions"]["right_point"][0],
                0,
                100,
            ),
            0,
            100,
        )

        shifted_iris = utils.color_shift(
            iris,
            utils.blend_colors(
                settings["skins"]["neon"]["fg_color_start"],
                settings["skins"]["neon"]["fg_color_end"],
                motion_progress / 100,
            ),
        )

        image.paste(
            shifted_iris,
            (int(eye_x - iris.width // 2), int(eye_y - iris.height // 2)),
            iris,
        )

        for disp in displays:
            disp.image(image)
        last_redraw = time.time()
