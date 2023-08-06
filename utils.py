from PIL import ImageColor

import json
import serial

def shift_hue(image, hue):
    image_hsv = image.convert('HSV')

    image_hue_shifted = image_hsv.copy()
    pixels = image_hue_shifted.load()
    width, height = image_hue_shifted.size
    for x in range(width):
        for y in range(height):
            h, s, v = pixels[x, y]
            h = (h + hue) % 256
            pixels[x, y] = (h, s, v)

    # Convert the image back to RGB
    return image_hue_shifted.convert('RGB')


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
    rgb1 = tuple(int(color1.strip("#")[i:i + 2], 16) for i in (0, 2, 4))
    rgb2 = tuple(int(color2.strip("#")[i:i + 2], 16) for i in (0, 2, 4))

    # Calculate the blended RGB values
    blended_rgb = tuple(int((1 - weight) * c1 + weight * c2) for c1, c2 in zip(rgb1, rgb2))

    # Convert RGB to hex color
    blended_hex = '#{:02x}{:02x}{:02x}'.format(*blended_rgb)

    return blended_hex


def map_range(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


def clamp(val, minn, maxn):
    """
    Clamp value to min/max
    """
    return max(min(maxn, val), minn)


def send_data(data: dict, ser: serial.Serial, prefix: str=''):
    for key, value in data.items():
        if isinstance(value, dict):
            send_data(value, ser, prefix=f"{prefix}{key}.")
        else:
            serialized_value = json.dumps(value)
            data = f"{prefix}{key}={serialized_value}\n"
            ser.write(data.encode())
