import time
from testlib import *


@test()
def test_color_bands(video: VideoChip):
    # Set 40 columns long mode.
    match video.chip_type:
        case VideoChipType.EF9345:
            tgs = 0x10
            pat = 0x37
        case VideoChipType.TS9347:
            tgs = 0x00
            pat = 0x33
    video.R1 = tgs
    video.ER0 = 0x81
    video.wait_not_busy()
    video.R1 = pat
    video.ER0 = 0x83
    video.wait_not_busy()

    # mat
    video.R1 = 0x08
    video.ER0 = 0x82
    video.wait_not_busy()

    # ror
    video.R1 = 0x08
    video.ER0 = 0x87
    video.wait_not_busy()

    # dor
    video.R1 = 0x00
    video.ER0 = 0x84
    video.wait_not_busy()

    # Fill top row.
    video.R0 = 0x01  # KRF/TLM with auto-increment.
    video.R1 = ord("x")
    video.R2 = 0
    video.R6 = 0  # y
    video.R7 = 0  # x
    for x in range(40):
        fg = x // 5
        bg = 7 - fg
        video.ER3 = (fg << 4) | bg
        video.wait_not_busy()

    # Copy from top row into all the other ones.
    for y in range(8, 25 + 8):
        video.R4 = y  # y
        video.R5 = 0  # x
        video.R6 = 0  # y
        video.R7 = 0  # x
        video.ER0 = 0xF5  # MVT
        video.wait_not_busy()

    time.sleep(0.5)

    screenshot = video.rgb_screenshot()
    assert check_images_equal(
        screenshot,
        "test_colors_data/test_color_bands.png",
    )


if __name__ == "__main__":
    test_main()
