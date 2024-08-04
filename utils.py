import enum
from PIL import ImageColor

import json
import serial


def shift_hue(image, hue):
    image_hsv = image.convert("HSV")

    image_hue_shifted = image_hsv.copy()
    pixels = image_hue_shifted.load()
    width, height = image_hue_shifted.size
    for x in range(width):
        for y in range(height):
            h, s, v = pixels[x, y]
            h = (h + hue) % 256
            pixels[x, y] = (h, s, v)

    # Convert the image back to RGB
    return image_hue_shifted.convert("RGB")


def color_shift(image, hex_color):
    target_rgb = ImageColor.getrgb(hex_color)
    red, green, blue = target_rgb

    # Iterate over each pixel and shift the red channel
    pixels = image.load()
    width, height = image.size
    for x in range(width):
        for y in range(height):
            _, _, _, alpha = pixels[x, y]
            pixels[x, y] = (red, green, blue, alpha)

    return image


def blend_colors(color1, color2, weight):
    # Convert hex colors to RGB
    rgb1 = tuple(int(color1.strip("#")[i : i + 2], 16) for i in (0, 2, 4))
    rgb2 = tuple(int(color2.strip("#")[i : i + 2], 16) for i in (0, 2, 4))

    # Calculate the blended RGB values
    blended_rgb = tuple(
        int((1 - weight) * c1 + weight * c2) for c1, c2 in zip(rgb1, rgb2)
    )

    # Convert RGB to hex color
    blended_hex = "#{:02x}{:02x}{:02x}".format(*blended_rgb)

    return blended_hex


def map_range(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


def clamp(val, minn, maxn):
    """
    Clamp value to min/max
    """
    return max(min(maxn, val), minn)


def send_data(data: dict, ser: serial.Serial, prefix: str = ""):
    for key, value in data.items():
        if isinstance(value, dict):
            send_data(value, ser, prefix=f"{prefix}{key}.")
        else:
            serialized_value = json.dumps(value)
            data = f"{prefix}{key}={serialized_value}\n"
            ser.write(data.encode())


def cubic_in_out(t):
    """
    CubicInOut Easing Curve
    """
    if t < 0.5:
        return 4 * t**3
    else:
        return 1 - (-2 * t + 2) ** 3 / 2


def step_jump_curve(t):
    """
    Round input to the nearest 0.5
    """
    return round(t * 2) / 2


def reflect_mod(value, max_value):
    """
    Custom modulo function that starts decreasing after reaching the max value.

    Parameters:
    value (float): The input value to be adjusted.
    max_value (float): The maximum value at which the behavior changes.

    Returns:
    float: The adjusted value.
    """
    if max_value <= 0:
        raise ValueError("max_value must be greater than 0")

    # Calculate the equivalent position in the range [0, 2*max_value]
    mod_value = value % (2 * max_value)

    # If in the second half, reflect it back
    if mod_value > max_value:
        return 2 * max_value - mod_value

    return mod_value


class ExtendedIntEnum(enum.IntEnum):
    """
    Extended IntEnum Class
    Adds list() function
    """

    @classmethod
    def list(cls):
        """
        Return list of enumerations
        """
        return list(map(lambda c: c.value, cls))
