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
