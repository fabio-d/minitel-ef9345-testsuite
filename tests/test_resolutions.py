import time
from testlib import *


# 40 columns long mode, non-interlaced.
@test()
def test_40columns(video: VideoChip):
    # Set TGS.
    match video.chip_type:
        case VideoChipType.EF9345:
            video.R1 = 0x10
        case VideoChipType.TS9347:
            video.R1 = 0x00
    video.ER0 = 0x81
    video.wait_not_busy()

    # Set PAT.
    video.R1 = 0x00
    video.ER0 = 0x83
    video.wait_not_busy()

    screenshot = video.screenshot()
    assert screenshot.width == 2 + 40 * 8 + 2
    assert screenshot.height == 2 + 25 * 10 + 2


# 80 columns long mode, non-interlaced.
@test()
def test_80columns(video: VideoChip):
    # Set TGS.
    match video.chip_type:
        case VideoChipType.EF9345:
            video.R1 = 0xD0
        case VideoChipType.TS9347:
            video.R1 = 0xC0
    video.ER0 = 0x81
    video.wait_not_busy()

    # Set PAT.
    video.R1 = 0x00
    video.ER0 = 0x83
    video.wait_not_busy()

    screenshot = video.screenshot()
    assert screenshot.width == 2 + 80 * 6 + 2
    assert screenshot.height == 2 + 25 * 10 + 2


# 40 columns long mode, non-interlaced, 525 lines.
@test(restrict=VideoChipType.EF9345)
def test_40columns_525lines(video: VideoChip):
    # Set TGS.
    video.R1 = 0x11
    video.ER0 = 0x81
    video.wait_not_busy()

    # Set PAT.
    video.R1 = 0x00
    video.ER0 = 0x83
    video.wait_not_busy()

    screenshot = video.screenshot()
    assert screenshot.width == 2 + 40 * 8 + 2
    assert screenshot.height == 2 + 21 * 10 + 2


# 80 columns long mode, non-interlaced, 525 lines.
@test(restrict=VideoChipType.EF9345)
def test_80columns_525lines(video: VideoChip):
    # Set TGS.
    video.R1 = 0xD1
    video.ER0 = 0x81
    video.wait_not_busy()

    # Set PAT.
    video.R1 = 0x00
    video.ER0 = 0x83
    video.wait_not_busy()

    screenshot = video.screenshot()
    assert screenshot.width == 2 + 80 * 6 + 2
    assert screenshot.height == 2 + 21 * 10 + 2


if __name__ == "__main__":
    test_main()
