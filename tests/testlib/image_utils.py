from typing import Union
import PIL.Image
import PIL.ImageChops


def check_images_equal(
    a: PIL.Image.Image,
    b: Union[PIL.Image.Image, str],
) -> bool:
    if isinstance(b, str):
        b = PIL.Image.open(b)
    a = a.convert("RGB")
    b = b.convert("RGB")
    diff = PIL.ImageChops.difference(a, b)
    if diff.getbbox() is None:
        return True

    r_binarized = diff.getchannel("R").point(lambda v: v != 0, mode="1")
    g_binarized = diff.getchannel("G").point(lambda v: v != 0, mode="1")
    b_binarized = diff.getchannel("B").point(lambda v: v != 0, mode="1")
    highlight = PIL.ImageChops.logical_or(r_binarized, g_binarized)
    highlight = PIL.ImageChops.logical_or(highlight, b_binarized)
    # highlight.show() # uncomment to show differences

    return False
