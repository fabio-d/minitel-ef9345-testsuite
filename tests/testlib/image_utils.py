import PIL.Image
import PIL.ImageChops


def save_image(path: str, *image: PIL.Image.Image):
    """
    Saves the given image(s) as a PNG file.

    If more than one image is given, it save in Animated PNG (APNG) format.
    """
    image_count = len(image)
    assert image_count > 0

    assert all(img.size == image[0].size for img in image[1:])
    converted = [img.convert("RGB") for img in image]

    if image_count == 1:
        converted[0].save(
            path,
            format="png",
        )
    else:
        converted[0].save(
            path,
            format="png",
            append_images=converted[1:],
            duration=500,
            loop=0,
            save_all=True,
        )


def assert_image(path: str, *image: PIL.Image.Image, show_diffs: bool = False):
    """
    Asserts that the given image(s) match the given PNG file.

    If the `show_diffs` argument is set, a debug image highlighting the
    differences is shown before failing.
    """
    loaded = PIL.Image.open(path, formats=["png"])

    image_count = len(image)
    assert image_count == loaded.n_frames

    assert all(img.size == loaded.size for img in image)

    # Create a canvas to store the differences we find.
    # For each considered image, we will store (left to right):
    #  - the input image
    #  - the template image
    #  - the map of differing pixels
    mtx = PIL.Image.new("RGB", (loaded.width * 3, loaded.height * len(image)))
    have_diffs = False
    for idx, input_image in enumerate(image):
        loaded.seek(idx)
        converted_input = input_image.convert("RGB")
        converted_template = loaded.convert("RGB")
        mtx.paste(converted_input, (0, loaded.height * idx))
        mtx.paste(converted_template, (loaded.width, loaded.height * idx))

        cmp = PIL.ImageChops.difference(converted_input, converted_template)
        if cmp.getbbox() is not None:
            r_binarized = cmp.getchannel("R").point(lambda v: v != 0, mode="1")
            g_binarized = cmp.getchannel("G").point(lambda v: v != 0, mode="1")
            b_binarized = cmp.getchannel("B").point(lambda v: v != 0, mode="1")
            highlight = PIL.ImageChops.logical_or(r_binarized, g_binarized)
            highlight = PIL.ImageChops.logical_or(highlight, b_binarized)
            mtx.paste(highlight, (loaded.width * 2, loaded.height * idx))
            have_diffs = True

    if have_diffs and show_diffs:
        mtx.show()
    assert not have_diffs
