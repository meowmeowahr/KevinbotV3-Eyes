from PIL import Image


class AssetManager:
    def __init__(self):
        self._logo = Image.open("assets/logo.png")
        self._metal_iris = Image.open("assets/metal/iris.png")
        self._aluminum = Image.open("assets/metal/aluminum.png")

    @property
    def logo(self) -> Image.Image:
        return self._logo

    @property
    def iris(self) -> Image.Image:
        return self._metal_iris

    @property
    def aluminum(self) -> Image.Image:
        return self._aluminum
