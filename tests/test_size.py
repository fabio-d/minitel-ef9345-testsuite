import time
from testlib import *


def test_double_size_and_cursor_generator(video: VideoChip):
    for globally_doubled in [False, True]:
        for mat_extra, descr in [(0x00, "complemented"), (0x10, "underline")]:
            if globally_doubled:
                mat_extra |= 0x80
                descr += "_globally_doubled"
            for pos in range(2):
                ref_name = f"double_width{["L", "R"][pos]}{descr}"
                yield ref_name, True, False, mat_extra, pos, ref_name
            for pos in range(2):
                ref_name = f"double_height{["T", "B"][pos]}{descr}"
                yield ref_name, False, True, mat_extra, pos, ref_name
            for pos in range(4):
                ref_name = f"double_both{["TL", "TR", "BL", "BR"][pos]}{descr}"
                yield ref_name, True, True, mat_extra, pos, ref_name


@test(parametric=test_double_size_and_cursor_generator)
def test_double_size_and_cursor(
    video: VideoChip,
    double_width: bool,
    double_height: bool,
    mat_extra: int,
    cursor_position_index: int,
    ref_name: str,
):
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
    video.R1 = 0x48 | mat_extra
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

    # Draw "@".
    match (double_width, double_height):
        case True, False:
            positions = [(0, 8), (1, 8)]
        case False, True:
            positions = [(0, 8), (0, 9)]
        case True, True:
            positions = [(0, 8), (1, 8), (0, 9), (1, 9)]
    video.R0 = 0x01  # KRF/TLM with auto-increment.
    video.R2 = (0x08 if double_width else 0) | (0x02 if double_height else 0)
    video.R3 = 0x70  #  white on black
    video.R1 = ord("X")
    for x, y in positions:
        video.R7 = x
        video.ER6 = y
        video.wait_not_busy()

    # Set cursor position.
    cursor_x, cursor_y = positions[cursor_position_index]  # x, y
    video.R6 = cursor_y
    video.R7 = cursor_x

    reference = Screenshot.load(
        "test_size_data/test_double_size_and_cursor_%s.png" % ref_name
    )
    video.expect_screenshot(reference, ChannelSet.RGB)


if __name__ == "__main__":
    test_main()
