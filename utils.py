from PIL import ImageColor

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
