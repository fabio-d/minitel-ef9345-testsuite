import time
from testlib import *


@test()
def test_40columns_attributes(video: VideoChip):
    # Set 40 columns long mode.
    match video.chip_type:
        case VideoChipType.EF9345:
            tgs = 0x10
            pat_base = 0x07
        case VideoChipType.TS9347:
            tgs = 0x00
            pat_base = 0x03
    video.R1 = tgs
    video.ER0 = 0x81
    video.wait_not_busy()
    video.R1 = pat_base
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

    # Draw color stripes with varying attributes.
    video.R0 = 0x01  # KRF/TLM with auto-increment.
    for row, a, b, description in [
        (10, 0x00, 0x00, "N=0, F=0, m=0, i=0"),
        (11, 0x00, 0x01, "N=0, F=0, m=0, i=1"),
        (12, 0x00, 0x04, "N=0, F=0, m=1, i=0"),
        (13, 0x00, 0x05, "N=0, F=0, m=1, i=1"),
        (15, 0x08, 0x00, "N=0, F=1, m=0, i=0"),
        (16, 0x08, 0x01, "N=0, F=1, m=0, i=1"),
        (17, 0x08, 0x04, "N=0, F=1, m=1, i=0"),
        (18, 0x08, 0x05, "N=0, F=1, m=1, i=1"),
        (20, 0x80, 0x00, "N=1, F=0, m=0, i=0"),
        (21, 0x80, 0x01, "N=1, F=0, m=0, i=1"),
        (22, 0x80, 0x04, "N=1, F=0, m=1, i=0"),
        (23, 0x80, 0x05, "N=1, F=0, m=1, i=1"),
        (25, 0x88, 0x00, "N=1, F=1, m=0, i=0"),
        (26, 0x88, 0x01, "N=1, F=1, m=0, i=1"),
        (27, 0x88, 0x04, "N=1, F=1, m=1, i=0"),
        (28, 0x88, 0x05, "N=1, F=1, m=1, i=1"),
    ]:
        video.R6 = row
        video.R7 = 0
        for x in range(8):
            fg = x
            bg = 7 - fg
            video.R3 = a | (fg << 4) | bg
            video.R2 = b
            video.ER1 = ord("@")
            video.wait_not_busy()
        video.R3 = 0x70  # white on black
        video.R2 = 0x01  # insert
        for c in f" {description:31s}"[:32]:
            video.ER1 = ord(c)
            video.wait_not_busy()

    # Render with different PAT values.
    for pat_extra, description in [
        (0x00, "Conceal=0, Flash=0, InsMode=Inlay"),
        (0x10, "Conceal=0, Flash=0, InsMode=Boxing"),
        (0x20, "Conceal=0, Flash=0, InsMode=ChrMark"),
        (0x30, "Conceal=0, Flash=0, InsMode=ActAreaMark"),
        (0x40, "Conceal=0, Flash=1, InsMode=Inlay"),
        (0x50, "Conceal=0, Flash=1, InsMode=Boxing"),
        (0x60, "Conceal=0, Flash=1, InsMode=ChrMark"),
        (0x70, "Conceal=0, Flash=1, InsMode=ActAreaMark"),
        (0x08, "Conceal=1, Flash=0, InsMode=Inlay"),
        (0x18, "Conceal=1, Flash=0, InsMode=Boxing"),
        (0x28, "Conceal=1, Flash=0, InsMode=ChrMark"),
        (0x38, "Conceal=1, Flash=0, InsMode=ActAreaMark"),
        (0x48, "Conceal=1, Flash=1, InsMode=Inlay"),
        (0x58, "Conceal=1, Flash=1, InsMode=Boxing"),
        (0x68, "Conceal=1, Flash=1, InsMode=ChrMark"),
        (0x78, "Conceal=1, Flash=1, InsMode=ActAreaMark"),
    ]:
        # Draw header.
        video.R0 = 0x01  # KRF/TLM with auto-increment.
        video.R3 = 0x70  # white on black
        video.R2 = 0x01  # insert
        video.R6 = 0  # y
        video.R7 = 0  # x
        for c in f"{description:40s}":
            video.ER1 = ord(c)
            video.wait_not_busy()

        # Set PAT.
        video.R1 = pat_base | pat_extra
        video.ER0 = 0x83
        time.sleep(0.5)

        if pat_extra & 0x40:
            screenshots = list(video.flashing_rgb_screenshot())
        else:
            screenshots = [video.rgb_screenshot()]
        assert_image(
            "test_colors_data/test_40columns_attributes_%02x.png" % pat_extra,
            *screenshots,
        )


if __name__ == "__main__":
    test_main()
