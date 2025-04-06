import PIL.Image


def test_images_equal(a: PIL.Image.Image, b: PIL.Image.Image) -> bool:
    assert a.format == b.format
    assert a.size == b.size
    return list(a.getdata()) == list(b.getdata())


def vertical_concat(*images: PIL.Image.Image) -> PIL.Image.Image:
    width = max(img.width for img in images)
    height = sum(img.height for img in images)
    result = PIL.Image.new("RGB", (width, height))
    y = 0
    for img in images:
        result.paste(img.convert("RGB"), (0, y))
        y += img.height
    return result
