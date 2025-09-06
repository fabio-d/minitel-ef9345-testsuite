import time
from testlib import *


@test()
def test_double_size_render(video: VideoChip):
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

    # Draw four characters with easily recognizable patterns in all possible
    # sizes.
    TEXT = r"/ \ < >"
    video.R0 = 0x01  # KRF/TLM with auto-increment.
    video.R3 = 0x07  # black on white

    # Row 8: regular size.
    video.R2 = 0x00
    video.R6 = 8  # y
    video.R7 = 0  # x
    for c in TEXT:
        video.ER1 = ord(c)
        video.wait_not_busy()

    # Row 10: double width.
    video.R2 = 0x08
    video.R6 = 10  # y
    video.R7 = 0  # x
    for c in TEXT:
        video.ER1 = ord(c)
        video.wait_not_busy()
        video.ER1 = ord(c)
        video.wait_not_busy()

    # Row 12 and 13: double height.
    video.R2 = 0x02
    video.R6 = 12  # y
    video.R7 = 0  # x
    for c in TEXT:
        video.ER1 = ord(c)
        video.wait_not_busy()
    video.R6 = 13  # y
    video.R7 = 0  # x
    for c in TEXT:
        video.ER1 = ord(c)
        video.wait_not_busy()

    # Row 15 and 16: double width and height.
    video.R2 = 0x0A
    video.R6 = 15  # y
    video.R7 = 0  # x
    for c in TEXT:
        video.ER1 = ord(c)
        video.wait_not_busy()
        video.ER1 = ord(c)
        video.wait_not_busy()
    video.R6 = 16  # y
    video.R7 = 0  # x
    for c in TEXT:
        video.ER1 = ord(c)
        video.wait_not_busy()
        video.ER1 = ord(c)
        video.wait_not_busy()

    reference = Screenshot.load("test_size_data/test_double_size_render.png")
    video.expect_screenshot(reference, ChannelSet.RGB)

    # mat
    video.R1 = 0x88  # set global double height bit too
    video.ER0 = 0x82
    video.wait_not_busy()

    reference = Screenshot.load(
        "test_size_data/test_double_size_render_globally_doubled.png"
    )
    video.expect_screenshot(reference, ChannelSet.RGB)


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


def test_double_size_in_service_row_generator(video: VideoChip):
    yield "top", False
    if video.chip_type == VideoChipType.TS9347:
        yield "bottom", True


@test(parametric=test_double_size_in_service_row_generator)
def test_double_size_in_service_row(video: VideoChip, low_service_row: bool):
    # Set 40 columns long mode. On the TS9347, position the service row
    # according to the test parameter.
    match video.chip_type:
        case VideoChipType.EF9345:
            tgs = 0x10
            pat = 0x37
        case VideoChipType.TS9347:
            tgs = 0x01 if low_service_row else 0x00  # = bottom if set
            pat = 0x33
    video.R1 = tgs
    video.ER0 = 0x81
    video.wait_not_busy()
    video.R1 = pat
    video.ER0 = 0x83
    video.wait_not_busy()

    # MAT
    video.R1 = 0x08
    video.ER0 = 0x82
    video.wait_not_busy()

    # ROR
    video.R1 = 0x08
    video.ER0 = 0x87
    video.wait_not_busy()

    # DOR
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

    video.R0 = 0x01  # KRF/TLM with auto-increment.
    video.R3 = 0x70  # white on black
    video.R1 = ord("X")

    for y in [0, 8, 9]:
        video.R6 = y
        video.R7 = 0  # x

        # Draw with regular size.
        video.ER2 = 0
        video.wait_not_busy()

        # Draw with double width.
        video.ER2 = 0x08
        video.wait_not_busy()
        video.ER2 = 0x08
        video.wait_not_busy()

        # Draw with double height.
        video.ER2 = 0x02
        video.wait_not_busy()

        # Draw with double width and height.
        video.ER2 = 0x0A
        video.wait_not_busy()
        video.ER2 = 0x0A
        video.wait_not_busy()

    reference = Screenshot.load(
        "test_size_data/test_double_size_in_service_row_%s.png"
        % ("bottom" if low_service_row else "top")
    )
    video.expect_screenshot(reference, ChannelSet.RGB)


def test_nonuniform_double_size_generator(video: VideoChip):
    CASES = [
        # All normal sizes.
        ("", ""),
        # Double width, double height and both at top-left corner.
        ("AB", ""),
        ("", "AE"),
        ("ABEF", "ABEF"),
        # Double width, double height and both after a double width column.
        ("AEIMBC", ""),
        ("AEIM", "BF"),
        ("AEIMBCFG", "BCFG"),
        # Double width, double height and both after a double height row.
        ("EF", "ABCD"),
        ("", "ABCDEI"),
        ("EFIJ", "ABCDEFIJ"),
        # Double width, double height and both after double width+height row/column.
        ("ABCDEIMFG", "ABCDEIM"),
        ("ABCDEIM", "ABCDEIMFK"),
        ("ABCDEIMFGKL", "ABCDEIMFGKL"),
        # Lone double-sized characters.
        ("F", ""),
        ("", "F"),
        ("F", "F"),
    ]
    for dw_list, dh_list in CASES:
        ref_name = "dw%s_dh%s" % (
            dw_list if dw_list else "NONE",
            dh_list if dh_list else "NONE",
        )
        yield ref_name, dw_list, dh_list, ref_name


# According to the datasheet, double-sized rendering requires all the characters
# at the occupied positions to be the same (e.g. "AA" in case of double width).
# This test validates the undocumented behavior in case those characters differ,
# both in the characters and in their colors.
@test(parametric=test_nonuniform_double_size_generator)
def test_nonuniform_double_size(
    video: VideoChip,
    double_width_letters: str,
    double_height_letters: str,
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

    # MAT
    video.R1 = 0x08
    video.ER0 = 0x82
    video.wait_not_busy()

    # ROR
    video.R1 = 0x08
    video.ER0 = 0x87
    video.wait_not_busy()

    # DOR
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

    # Draw a 4x4 matrix with consecutive letters:
    #  ABCD
    #  EFGH
    #  JKLM
    #  NOPQ
    # For each position set the double-width and double-height attributes
    # are set only on some letters, depending on the current test parameters.
    video.R0 = 0x01  # KRF/TLM with auto-increment.
    for y in range(4):
        video.R6 = 10 + y
        video.R7 = 2  # x
        for x in range(4):
            letter = chr(ord("A") + y * 4 + x)

            # Set double width and height attributes.
            attr_b = 0
            if letter in double_width_letters:
                attr_b |= 0x08
            if letter in double_height_letters:
                attr_b |= 0x02
            video.R2 = attr_b

            # Set colors so that the character grid is clearly visible.
            # This also verifies that size attributes don't influence colors.
            fgcolor = (x + 3 * y) % 7 + 1
            bgcolor = fgcolor ^ 0x7
            video.R3 = (fgcolor << 4) | bgcolor

            video.ER1 = ord(letter)
            video.wait_not_busy()

    reference = Screenshot.load(
        "test_size_data/test_nonuniform_double_size_%s.png" % ref_name
    )
    video.expect_screenshot(reference, ChannelSet.RGB)


# This test further validates the rendering of a single character with the
# double-width attribute, followed by a blank space (optionally underlined).
@test(
    parametric={
        "b0": (0, ord("X"), False),  # just an X.
        "b1": (1, ord("X"), False),  # underlined X.
        "b3": (2, 0x59, False),  # a mosaic character.
        "b0u": (0, ord("X"), True),  # just an X.
        "b1u": (1, ord("X"), True),  # underlined X.
        "b3u": (2, 0x59, True),  # a mosaic character.
    }
)
def test_lone_double_width(
    video: VideoChip, b: int, c: int, underline_follows: bool
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

    # MAT
    video.R1 = 0x08
    video.ER0 = 0x82
    video.wait_not_busy()

    # ROR
    video.R1 = 0x08
    video.ER0 = 0x87
    video.wait_not_busy()

    # DOR
    video.R1 = 0x00
    video.ER0 = 0x84
    video.wait_not_busy()

    # Clear screen.
    video.R1 = ord(" ")
    video.R2 = 0x00
    video.R3 = 0x70  # white on black
    video.R6 = 0  # y
    video.R7 = 0  # x
    video.ER0 = 0x05  # CLF/CLL
    time.sleep(0.5)
    video.ER0 = 0x91  # NOP to stop it.
    video.wait_not_busy()

    # Draw it.
    video.R1 = c
    video.R2 = (b << 4) | 0x08  # double-width
    video.R3 = 0x70  # white on black
    video.R6 = 0x08  # y
    video.R7 = 0  # x
    video.ER0 = 0x01  # KRF/TLM with auto-increment.
    video.wait_not_busy()

    if underline_follows:
        video.R1 = ord(" ")
        video.ER2 = 0x10  # underlined
        video.wait_not_busy()

    reference = Screenshot.load(
        "test_size_data/test_lone_double_width_b%d%s.png"
        % (b, "u" if underline_follows else "")
    )
    video.expect_screenshot(reference, ChannelSet.RGB)


if __name__ == "__main__":
    test_main()
