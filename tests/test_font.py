import time
import PIL.Image
from testlib import *


@test(
    parametric={
        "b0": (0,),
        "b1": (1,),
        "b2": (2,),
        "b3": (3,),
        "b4": (4,),
        "b5": (5,),
        "b6": (6,),
        "b7": (7,),
    }
)
def test_read_ind(video: VideoChip, b: int):
    # Set TGS to ensure the chip is in a valid video mode.
    match video.chip_type:
        case VideoChipType.EF9345:
            video.R1 = 0x10
        case VideoChipType.TS9347:
            video.R1 = 0x00
    video.ER0 = 0x81
    video.wait_not_busy()

    bits = []
    video.R0 = 0x88  # IND from ROM
    for c in range(0, 128, 4):
        video.R6 = (0x20 if (b & 4) else 0) | ((c & 0x7C) >> 2)
        for sn_and_low_c in range(16 * 4):
            video.ER7 = (
                (0x80 if (b & 1) else 0)
                | (0x40 if (b & 2) else 0)
                | sn_and_low_c
            )
            video.wait_not_busy()
            bits.append(video.R1)

    reference = PIL.Image.open(
        "test_font_data/test_read_ind_%s_b%d.png" % (video.chip_type.value, b),
        formats=["png"],
    ).convert("1")
    actual = PIL.Image.frombytes(
        "1", (32, len(bits) // 4), bytes(bits), "raw", "1;R"
    )
    assert test_images_equal(actual, reference)


@test(
    parametric={
        "b0": (0,),
        "b1": (1,),
        "b2": (2,),
        "b3": (3,),
        "b4": (4,),
        "b5": (5,),
        "b6": (6,),
        "b7": (7,),
    }
)
def test_render_40columns(video: VideoChip, b: int):
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

    video.R7 = 0  # move the cursor out of the way of the rendered font

    reference = Screenshot.load(
        "test_font_data/test_render_40columns_%s_b%d.png"
        % (
            video.chip_type.value,
            b,
        )
    )
    video.expect_screenshot(reference, ChannelSet.RGB)


def test_cursor_underline_40columns_generator(video: VideoChip):
    # The underline cursor should be visible in alphanumeric fonts...
    yield "G0", 0x00, ord("A"), "alphanumeric"
    yield "G0+underline", 0x00, ord("A"), "alphanumeric"  # same rendering as G0

    # ...but not in semigraphical fonts.
    yield "G10", 0x20, 0x66, "mosaic"
    match video.chip_type:
        case VideoChipType.EF9345:
            yield "G11", 0x30, 0x0A, "EF9345_extra"
        case VideoChipType.TS9347:
            yield "GOE", 0x30, 0x0A, "TS9347_extra"


@test(parametric=test_cursor_underline_40columns_generator)
def test_cursor_underline_40columns(
    video: VideoChip,
    b: int,
    c: int,
    file_name: str,
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
    video.R1 = 0x58  # fixed underlined cursor
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

    # Print the character being tested 3 times and leave the cursor on it.
    video.R0 = 0x00  # KRF/TLM
    video.R1 = c  # C
    video.R2 = b  # B
    video.R3 = 0x70  # A
    video.R6 = 0  # y
    for x in [0, 2, 4]:
        video.ER7 = x
        video.wait_not_busy()

    reference = Screenshot.load(
        "test_font_data/test_cursor_underline_40columns_%s.png" % file_name
    )
    video.expect_screenshot(reference, ChannelSet.RGB)


@test()
def test_render_80columns(video: VideoChip):
    # Set 80 columns long mode.
    match video.chip_type:
        case VideoChipType.EF9345:
            tgs = 0xD0
            pat = 0x37
        case VideoChipType.TS9347:
            tgs = 0xC0
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
    video.R1 = 0x07
    video.ER0 = 0x84
    video.wait_not_busy()

    # Fill rows.
    video.R0 = 0x51  # KRL with auto-increment.
    video.R3 = 0x00
    for row in range(25):
        match row:
            case 0:
                text = b"Font in 80 columns mode"
            case 2:
                text = b"       _0  _1  _2  _3  _4  _5  _6  _7  _8  _9  _A  _B  _C  _D  _E  _F"
            case 4 | 6 | 8 | 10 | 12 | 14 | 16 | 18 | 20 | 22:
                # Only the TS9347 can show characters with top_bits = 8 and 9.
                top_bits = (row - 4) // 2
                if top_bits < 8 or video.chip_type == VideoChipType.TS9347:
                    text = b"C=%x_ \x0e " % top_bits
                    for i in range(16):
                        text += bytes([(top_bits << 4) | i, *b"   "])
                else:
                    text = b""
            case _:
                text = b""

        video.R6 = 0 if row == 0 else (row + 7)
        video.R7 = 0
        for c in (text + b" " * 80)[:80]:
            video.ER1 = c
            video.wait_not_busy()

    reference = Screenshot.load(
        "test_font_data/test_render_80columns_%s.png" % video.chip_type.value
    )
    video.expect_screenshot(reference, ChannelSet.RGB)


def test_cursor_underline_80columns_generator(video: VideoChip):
    # The underline cursor should be visible.
    yield "G0", 0x0, ord("A"), "alphanumeric"

    # The underline cursor should *not* be visible if the U attribute is set.
    yield "G0+underline", 0x2, ord("A"), "alphanumeric_underlined"

    match video.chip_type:
        case VideoChipType.EF9345:
            yield "mosaic", 0x8, 0xE6, "EF9345_mosaic"
        case VideoChipType.TS9347:
            yield "extra", 0x0, 0x8A, "TS9347_extra"
            yield "extra+underline", 0x2, 0x8A, "TS9347_extra_underlined"


@test(parametric=test_cursor_underline_80columns_generator)
def test_cursor_underline_80columns(
    video: VideoChip,
    a: int,
    c: int,
    file_name: str,
):
    # Set 80 columns long mode.
    match video.chip_type:
        case VideoChipType.EF9345:
            tgs = 0xD0
            pat = 0x37
        case VideoChipType.TS9347:
            tgs = 0xC0
            pat = 0x33
    video.R1 = tgs
    video.ER0 = 0x81
    video.wait_not_busy()
    video.R1 = pat
    video.ER0 = 0x83
    video.wait_not_busy()

    # mat
    video.R1 = 0x58
    video.ER0 = 0x82
    video.wait_not_busy()

    # ror
    video.R1 = 0x08
    video.ER0 = 0x87
    video.wait_not_busy()

    # dor
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

    # Print the character being tested 3 times and leave the cursor on it.
    video.R0 = 0x50  # KRL
    video.R1 = c  # C
    video.R3 = (a << 4) | a  # A
    video.R6 = 0  # y
    for x in [0, 1, 2]:
        video.ER7 = x
        video.wait_not_busy()

    reference = Screenshot.load(
        "test_font_data/test_cursor_underline_80columns_%s.png" % file_name
    )
    video.expect_screenshot(reference, ChannelSet.RGB)


if __name__ == "__main__":
    test_main()
