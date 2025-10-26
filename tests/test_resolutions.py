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


def test_areas_generator(chip_type: VideoChipType):
    match chip_type:
        case VideoChipType.EF9345:
            areas = [
                0x01,  # Service Row Only
                0x02,  # Upper Bulk Only
                0x04,  # Lower Bulk Only
                0x07,  # All of the above
                0x00,  # None
            ]
        case VideoChipType.TS9347:
            areas = [
                0x01,  # Service Row Only
                0x02,  # Bulk Only
                0x03,  # All of the above
                0x00,  # None
            ]

    # It is interesting to test both values of the lowest TGS bit, on both
    # chips, for different reasons:
    # - on the EF9345, it enables the 525 lines mode
    # - on the TS9347, it moves the service row to the bottom
    for tgs_extra in [0, 1]:
        for pat_extra in areas:
            yield (
                f"pat{pat_extra:02x}tgs{tgs_extra:02x}",
                pat_extra,
                tgs_extra,
                0x00,
            )
            yield (
                f"pat{pat_extra:02x}tgs{tgs_extra:02x}_globally_doubled",
                pat_extra,
                tgs_extra,
                0x80,
            )


# 40 columns long mode, non-interlaced.
@test()
def test_areas_40columns(video: VideoChip):
    # Set ROR.
    video.R1 = 0x08
    video.ER0 = 0x87
    video.wait_not_busy()

    # Set DOR.
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

    # Write the row number in every row.
    video.R0 = 0x01  # KRF/TLM with auto-increment.
    video.R2 = 0x00  # B
    video.R3 = 0x70  # A
    for y in [0, *range(8, 32)]:
        video.R6 = y
        video.R7 = 0  # x
        for c in str(y):
            video.ER1 = ord(c)
            video.wait_not_busy()

    # Draw a double-height unique character at each boundary crossing, on a
    # "background" of normal-sized Xs (to detect unwanted attribute "leakage").
    for y in [0, 8, 19, 20, 31]:
        video.R6 = y
        video.R1 = ord('X')
        for x in range(34, 39):
            video.ER7 = x
            video.wait_not_busy()
    video.R0 = 0x00  # KRF/TLM without auto-increment.
    video.R2 = 0x02  # double heigth
    video.R7 = 35  # x
    video.R1 = ord("A")
    video.ER6 = 0  # y
    video.wait_not_busy()
    video.ER6 = 8  # y
    video.wait_not_busy()
    video.R7 = 36  # x
    video.R1 = ord("B")
    video.ER6 = 19  # y
    video.wait_not_busy()
    video.ER6 = 20  # y
    video.wait_not_busy()
    video.R7 = 37  # x
    video.R1 = ord("C")
    video.ER6 = 31  # y
    video.wait_not_busy()

    for ref_name, pat_extra, tgs_extra, mat_extra in test_areas_generator(
        video.chip_type
    ):
        # Set TGS.
        match video.chip_type:
            case VideoChipType.EF9345:
                video.R1 = 0x10 | tgs_extra
            case VideoChipType.TS9347:
                video.R1 = 0x00 | tgs_extra
        video.ER0 = 0x81
        video.wait_not_busy()

        # Set PAT.
        video.R1 = 0x30 | pat_extra
        video.ER0 = 0x83
        video.wait_not_busy()

        # Set MAT.
        video.R1 = 0x08 | mat_extra
        video.ER0 = 0x82
        video.wait_not_busy()

        reference = Screenshot.load(
            "test_resolutions_data/test_areas_40columns_%s_%s.png"
            % (video.chip_type.value, ref_name)
        )
        video.expect_screenshot(reference, ChannelSet.RGB)


# 80 columns long mode, non-interlaced.
@test()
def test_areas_80columns(video: VideoChip):
    # Set ROR.
    video.R1 = 0x08
    video.ER0 = 0x87
    video.wait_not_busy()

    # Set DOR.
    video.R1 = 0x07
    video.ER0 = 0x84
    video.wait_not_busy()

    # Clear screen.
    video.R1 = ord(" ")
    video.R2 = ord(" ")
    video.R3 = 0x00
    video.R6 = 0  # y
    video.R7 = 0  # x
    video.ER0 = 0x05  # CLF/CLL
    time.sleep(0.5)
    video.ER0 = 0x91  # NOP to stop it.
    video.wait_not_busy()

    # Write the row number in every row.
    video.R0 = 0x51  # KRL with auto-increment.
    video.R3 = 0x00
    for y in [0, *range(8, 32)]:
        video.R6 = y
        video.R7 = 0  # x
        for c in str(y):
            video.ER1 = ord(c)
            video.wait_not_busy()

    for ref_name, pat_extra, tgs_extra, mat_extra in test_areas_generator(
        video.chip_type
    ):
        # Set TGS.
        match video.chip_type:
            case VideoChipType.EF9345:
                video.R1 = 0xD0 | tgs_extra
            case VideoChipType.TS9347:
                video.R1 = 0xC0 | tgs_extra
        video.ER0 = 0x81
        video.wait_not_busy()

        # Set PAT.
        video.R1 = 0x30 | pat_extra
        video.ER0 = 0x83
        video.wait_not_busy()

        # Set MAT.
        video.R1 = 0x08 | mat_extra
        video.ER0 = 0x82
        video.wait_not_busy()

        reference = Screenshot.load(
            "test_resolutions_data/test_areas_80columns_%s_%s.png"
            % (video.chip_type.value, ref_name)
        )
        video.expect_screenshot(reference, ChannelSet.RGB)


if __name__ == "__main__":
    test_main()
