import time
from testlib import *


@test()
def test_render_40columns_b0(video: VideoChip):
    _test_render_40columns_inner(video, 0)


@test()
def test_render_40columns_b1(video: VideoChip):
    _test_render_40columns_inner(video, 1)


@test()
def test_render_40columns_b2(video: VideoChip):
    _test_render_40columns_inner(video, 2)


@test()
def test_render_40columns_b3(video: VideoChip):
    _test_render_40columns_inner(video, 3)


@test()
def test_render_40columns_b4(video: VideoChip):
    _test_render_40columns_inner(video, 4)


@test()
def test_render_40columns_b5(video: VideoChip):
    _test_render_40columns_inner(video, 5)


@test()
def test_render_40columns_b6(video: VideoChip):
    _test_render_40columns_inner(video, 6)


@test()
def test_render_40columns_b7(video: VideoChip):
    _test_render_40columns_inner(video, 7)


def _test_render_40columns_inner(video: VideoChip, b: int):
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

    # Clear screen.
    video.R1 = 0x00
    video.R2 = 0x00
    video.R3 = 0x00
    video.R6 = 0  # y
    video.R7 = 0  # x
    video.ER0 = 0x05  # CLF/CLL
    time.sleep(0.5)
    video.ER0 = 0x91  # NOP to stop it.
    video.wait_not_busy()

    # Show header at line 0.
    video.R0 = 0x01  # KRF/TLM with auto-increment.
    video.R2 = 0x00  # B
    video.R3 = 0x70  # A
    video.R6 = 0  # y
    video.R7 = 0  # x
    for c in "Font with B=0x%x_" % b:
        video.ER1 = ord(c)
        video.wait_not_busy()

    # Show header at lines 10-11.
    video.R6 = 10  # y
    video.R7 = 0  # x
    for c in "       _0  _1  _2  _3  _4  _5  _6  _7":
        video.ER1 = ord(c)
        video.wait_not_busy()
    video.R6 += 1  # y
    video.R7 = 0  # x
    for c in "       _8  _9  _A  _B  _C  _D  _E  _F":
        video.ER1 = ord(c)
        video.wait_not_busy()
    video.R6 += 1  # y

    # Fill rows.
    for top_bits in range(8):
        video.R7 = 0  # x

        video.R2 = 0x00  # alphanumeric text
        for c in "C=%x_ \x0e " % top_bits:
            video.ER1 = ord(c)
            video.wait_not_busy()

        init_x = video.R7
        video.R2 = b << 4
        for i in range(8):
            video.R7 = init_x + 4 * i
            video.ER1 = (top_bits << 4) | i
            video.wait_not_busy()
        video.R6 += 1
        for i in range(8):
            video.R7 = init_x + 4 * i
            video.ER1 = (top_bits << 4) | 8 | i
            video.wait_not_busy()
        video.R6 += 1  # y

    video.R7 = 0  # move the cursor of of the way of the rendered font

    time.sleep(0.5)

    screenshot = video.rgb_screenshot()
    assert check_images_equal(
        screenshot,
        "test_font_data/test_render_40columns_%s_b%d.png"
        % (video.chip_type.value, b),
    )


if __name__ == "__main__":
    test_main()
