import time
from testlib import *

# All the PAT bits that may affect how color and insert channels are rendered.
# Note: In 80 columns mode there is no conceal attribute.
ALL_PAT_CONFIGURATIONS_40COLUMNS = {  # pat_value -> description
    0x00: "Conceal=0, Flash=0, InsMode=Inlay",
    0x10: "Conceal=0, Flash=0, InsMode=Boxing",
    0x20: "Conceal=0, Flash=0, InsMode=ChrMark",
    0x30: "Conceal=0, Flash=0, InsMode=ActAreaMark",
    0x40: "Conceal=0, Flash=1, InsMode=Inlay",
    0x50: "Conceal=0, Flash=1, InsMode=Boxing",
    0x60: "Conceal=0, Flash=1, InsMode=ChrMark",
    0x70: "Conceal=0, Flash=1, InsMode=ActAreaMark",
    0x08: "Conceal=1, Flash=0, InsMode=Inlay",
    0x18: "Conceal=1, Flash=0, InsMode=Boxing",
    0x28: "Conceal=1, Flash=0, InsMode=ChrMark",
    0x38: "Conceal=1, Flash=0, InsMode=ActAreaMark",
    0x48: "Conceal=1, Flash=1, InsMode=Inlay",
    0x58: "Conceal=1, Flash=1, InsMode=Boxing",
    0x68: "Conceal=1, Flash=1, InsMode=ChrMark",
    0x78: "Conceal=1, Flash=1, InsMode=ActAreaMark",
}
ALL_PAT_CONFIGURATIONS_80COLUMNS = {  # pat_value -> description
    0x00: "Flash=0, InsMode=Inlay",
    0x10: "Flash=0, InsMode=Boxing",
    0x20: "Flash=0, InsMode=ChrMark",
    0x30: "Flash=0, InsMode=ActAreaMark",
    0x40: "Flash=1, InsMode=Inlay",
    0x50: "Flash=1, InsMode=Boxing",
    0x60: "Flash=1, InsMode=ChrMark",
    0x70: "Flash=1, InsMode=ActAreaMark",
}

# All the attributes that affect the output color and insert channels.
# Note: The TS9347 has an extra attribute (i2 - stored in B), that is only
# meaningful if the insert mode is "Boxing and Inlay" (see PAT) and i1 == 1.
ALL_COLOR_ATTRIBUTES_EF9345_40COLUMNS = {  # (a, b) -> description
    (0x00, 0x00): "N=0, F=0, m=0, i=0",
    (0x00, 0x01): "N=0, F=0, m=0, i=1",
    (0x00, 0x04): "N=0, F=0, m=1, i=0",
    (0x00, 0x05): "N=0, F=0, m=1, i=1",
    (0x08, 0x00): "N=0, F=1, m=0, i=0",
    (0x08, 0x01): "N=0, F=1, m=0, i=1",
    (0x08, 0x04): "N=0, F=1, m=1, i=0",
    (0x08, 0x05): "N=0, F=1, m=1, i=1",
    (0x80, 0x00): "N=1, F=0, m=0, i=0",
    (0x80, 0x01): "N=1, F=0, m=0, i=1",
    (0x80, 0x04): "N=1, F=0, m=1, i=0",
    (0x80, 0x05): "N=1, F=0, m=1, i=1",
    (0x88, 0x00): "N=1, F=1, m=0, i=0",
    (0x88, 0x01): "N=1, F=1, m=0, i=1",
    (0x88, 0x04): "N=1, F=1, m=1, i=0",
    (0x88, 0x05): "N=1, F=1, m=1, i=1",
}
ALL_COLOR_ATTRIBUTES_TS9347_40COLUMNS = {  # (a, b) -> description
    (0x00, 0x00): "N=0, F=0, m=0, i1=0",
    (0x00, 0x01): "N=0, F=0, m=0, i1=1, i2=0",
    (0x00, 0x41): "N=0, F=0, m=0, i1=1, i2=1",
    (0x00, 0x04): "N=0, F=0, m=1, i1=0",
    (0x00, 0x05): "N=0, F=0, m=1, i1=1, i2=0",
    (0x00, 0x45): "N=0, F=0, m=1, i1=1, i2=1",
    (0x08, 0x00): "N=0, F=1, m=0, i1=0",
    (0x08, 0x01): "N=0, F=1, m=0, i1=1, i2=0",
    (0x08, 0x41): "N=0, F=1, m=0, i1=1, i2=1",
    (0x08, 0x04): "N=0, F=1, m=1, i1=0",
    (0x08, 0x05): "N=0, F=1, m=1, i1=1, i2=0",
    (0x08, 0x45): "N=0, F=1, m=1, i1=1, i2=1",
    (0x80, 0x00): "N=1, F=0, m=0, i1=0",
    (0x80, 0x01): "N=1, F=0, m=0, i1=1, i2=0",
    (0x80, 0x41): "N=1, F=0, m=0, i1=1, i2=1",
    (0x80, 0x04): "N=1, F=0, m=1, i1=0",
    (0x80, 0x05): "N=1, F=0, m=1, i1=1, i2=0",
    (0x80, 0x45): "N=1, F=0, m=1, i1=1, i2=1",
    (0x88, 0x00): "N=1, F=1, m=0, i1=0",
    (0x88, 0x01): "N=1, F=1, m=0, i1=1, i2=0",
    (0x88, 0x41): "N=1, F=1, m=0, i1=1, i2=1",
    (0x88, 0x04): "N=1, F=1, m=1, i1=0",
    (0x88, 0x05): "N=1, F=1, m=1, i1=1, i2=0",
    (0x88, 0x45): "N=1, F=1, m=1, i1=1, i2=1",
}
ALL_COLOR_ATTRIBUTES_80COLUMNS = {  # a -> description
    0x0: "N=0, F=0, D=0",
    0x1: "N=0, F=0, D=1",
    0x4: "N=0, F=1, D=0",
    0x5: "N=0, F=1, D=1",
    0x8: "N=1, F=0, D=0",
    0x9: "N=1, F=0, D=1",
    0xC: "N=1, F=1, D=0",
    0xD: "N=1, F=1, D=1",
}

# All the MAT bits that may affect how the cursor is rendered.
ALL_MAT_CONFIGURATIONS = {  # mat_value => description
    0x00: "No cursor",
    0x40: "FixedComplemented",
    0x60: "FlashComplemented",
    0x50: "FixedUnderlined",
    0x70: "FlashUnderline",
}


def test_40columns_attributes_generator(video: VideoChip):
    for pat_extra, pat_descr in ALL_PAT_CONFIGURATIONS_40COLUMNS.items():
        yield f"pat{pat_extra:02x}", pat_extra, pat_descr


@test(parametric=test_40columns_attributes_generator)
def test_40columns_attributes(video: VideoChip, pat_extra: int, pat_descr: str):
    # Set 40 columns long mode.
    match video.chip_type:
        case VideoChipType.EF9345:
            tgs_bgr = 0x10
            tgs_bir = 0x10
            pat_base = 0x07
        case VideoChipType.TS9347:
            tgs_bgr = 0x00
            tgs_bir = 0x10
            pat_base = 0x03
    video.R1 = tgs_bgr
    video.ER0 = 0x81
    video.wait_not_busy()
    video.R1 = pat_base | pat_extra
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
    video.R1 = ord(" ")
    video.R2 = 0x01  # insert bit set
    video.R3 = 0x00
    video.R6 = 0  # y
    video.R7 = 0  # x
    video.ER0 = 0x05  # CLF/CLL
    time.sleep(0.5)
    video.ER0 = 0x91  # NOP to stop it.
    video.wait_not_busy()

    # Draw header.
    video.R0 = 0x01  # KRF/TLM with auto-increment.
    video.R3 = 0x70  # white on black
    video.R2 = 0x01  # insert
    video.R6 = 0  # y
    video.R7 = 0  # x
    for c in pat_descr:
        video.ER1 = ord(c)
        video.wait_not_busy()

    # Draw color stripes with varying attributes.
    match video.chip_type:
        case VideoChipType.EF9345:
            all_color_attributes = ALL_COLOR_ATTRIBUTES_EF9345_40COLUMNS
        case VideoChipType.TS9347:
            all_color_attributes = ALL_COLOR_ATTRIBUTES_TS9347_40COLUMNS
    video.R0 = 0x01  # KRF/TLM with auto-increment.
    for row, ((a, b), description) in enumerate(
        all_color_attributes.items(),
        start=8,
    ):
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
        for c in f" {description}":
            video.ER1 = ord(c)
            video.wait_not_busy()

    reference = Screenshot.load(
        "test_colors_data/test_40columns_attributes_%s_pat%02x.png"
        % (video.chip_type.value, pat_extra)
    )
    if tgs_bgr == tgs_bir:
        video.expect_screenshot(reference, ChannelSet.RGBI)
    else:
        video.R1 = tgs_bir
        video.ER0 = 0x81
        video.wait_not_busy()
        video.expect_screenshot(reference, ChannelSet.RBI)
        video.R1 = tgs_bgr
        video.ER0 = 0x81
        video.wait_not_busy()
        video.expect_screenshot(reference, ChannelSet.RGB)


def test_40columns_cursor_generator(video: VideoChip):
    match video.chip_type:
        case VideoChipType.EF9345:
            all_color_attributes = ALL_COLOR_ATTRIBUTES_EF9345_40COLUMNS
        case VideoChipType.TS9347:
            all_color_attributes = ALL_COLOR_ATTRIBUTES_TS9347_40COLUMNS

    for pat_extra, pat_descr in ALL_PAT_CONFIGURATIONS_40COLUMNS.items():
        for mat_extra, mat_descr in ALL_MAT_CONFIGURATIONS.items():
            if mat_extra == 0:
                # skip the "no cursor" test case, because it's already covered
                # by test_40columns_attributes.
                continue

            for (a, b), attr_descr in all_color_attributes.items():
                yield f"pat{pat_extra:02x}mat{mat_extra:02x}a{a:02x}b{b:02x}", pat_extra, pat_descr, mat_extra, mat_descr, a, b, attr_descr


@test(parametric=test_40columns_cursor_generator)
def test_40columns_cursor(
    video: VideoChip,
    pat_extra: int,
    pat_descr: str,
    mat_extra: int,
    mat_descr: str,
    a: int,
    b: int,
    attr_descr: str,
):
    # Set 40 columns long mode.
    match video.chip_type:
        case VideoChipType.EF9345:
            tgs_bgr = 0x10
            tgs_bir = 0x10
            pat_base = 0x07
        case VideoChipType.TS9347:
            tgs_bgr = 0x00
            tgs_bir = 0x10
            pat_base = 0x03
    video.R1 = tgs_bgr
    video.ER0 = 0x81
    video.wait_not_busy()
    video.R1 = pat_base | pat_extra
    video.ER0 = 0x83
    video.wait_not_busy()

    # mat
    video.R1 = 0x08 | mat_extra
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
    video.R1 = ord(" ")
    video.R2 = 0x01  # insert bit set
    video.R3 = 0x00
    video.R6 = 0  # y
    video.R7 = 0  # x
    video.ER0 = 0x05  # CLF/CLL
    time.sleep(0.5)
    video.ER0 = 0x91  # NOP to stop it.
    video.wait_not_busy()

    # Draw header.
    video.R0 = 0x01  # KRF/TLM with auto-increment.
    video.R3 = 0x70  # white on black
    video.R2 = 0x01  # insert
    video.R6 = 0  # y
    video.R7 = 0  # x
    for c in pat_descr:
        video.ER1 = ord(c)
        video.wait_not_busy()

    # Draw test pattern.
    video.R0 = 0x01  # KRF/TLM with auto-increment.
    video.R6 = 8  # y
    video.R7 = 0  # x
    for c in " EXAMPLE ":
        video.R3 = a | 0x13  # red on yellow
        video.R2 = b
        video.ER1 = ord(c)
        video.wait_not_busy()
    video.R3 = 0x70  # white on black
    video.R2 = 0x01  # insert
    for c in f" {attr_descr}":
        video.ER1 = ord(c)
        video.wait_not_busy()

    # Draw cursor type description.
    video.R0 = 0x01  # KRF/TLM with auto-increment.
    video.R6 = 9  # y
    video.R7 = 3  # x
    video.R3 = 0x70  # white on black
    video.R2 = 0x01  # insert
    for c in f"\x5E {mat_descr}"[:31]:
        video.ER1 = ord(c)
        video.wait_not_busy()

    # Position the cursor on the "A" of "EXAMPLE".
    video.R6 = 8  # y
    video.R7 = 3  # x

    reference = Screenshot.load(
        "test_colors_data/test_40columns_cursor_%s_pat%02xmat%02xa%02xb%02x.png"
        % (video.chip_type.value, pat_extra, mat_extra, a, b)
    )
    if tgs_bgr == tgs_bir:
        video.expect_screenshot(reference, ChannelSet.RGBI)
    else:
        video.R1 = tgs_bir
        video.ER0 = 0x81
        video.wait_not_busy()
        video.expect_screenshot(reference, ChannelSet.RBI)
        video.R1 = tgs_bgr
        video.ER0 = 0x81
        video.wait_not_busy()
        video.expect_screenshot(reference, ChannelSet.RGB)


def test_80columns_attributes_generator(video: VideoChip):
    for pat_extra, pat_descr in ALL_PAT_CONFIGURATIONS_80COLUMNS.items():
        yield f"pat{pat_extra:02x}", pat_extra, pat_descr


@test(parametric=test_80columns_attributes_generator)
def test_80columns_attributes(video: VideoChip, pat_extra: int, pat_descr: str):
    # Set 40 columns long mode.
    match video.chip_type:
        case VideoChipType.EF9345:
            tgs_bgr = 0xD0
            tgs_bir = 0xD0
            pat_base = 0x07
        case VideoChipType.TS9347:
            tgs_bgr = 0xC0
            tgs_bir = 0xD0
            pat_base = 0x03
    video.R1 = tgs_bgr
    video.ER0 = 0x81
    video.wait_not_busy()
    video.R1 = pat_base | pat_extra
    video.ER0 = 0x83
    video.wait_not_busy()

    # mat
    video.R1 = 0x02  # green
    video.ER0 = 0x82
    video.wait_not_busy()

    # ror
    video.R1 = 0x08
    video.ER0 = 0x87
    video.wait_not_busy()

    # dor: c1 = red+insert, c0 = blue
    match video.chip_type:
        case VideoChipType.EF9345:
            video.R1 = 0x94
        case VideoChipType.TS9347:
            # Note: On TS9347 DOR7 is used as Z4 (top bit of the current page),
            # which we want to be set to 0. Furthermore, it seems that the D
            # attribute acts itself as the insert bit, rather than selecting
            # either i0 or i1 as the datasheet seems to say.
            video.R1 = 0x14
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

    # Draw header.
    video.R0 = 0x51  # KRL with auto-increment.
    video.R3 = 0x11  # c1
    video.R6 = 0  # y
    video.R7 = 0  # x
    for c in pat_descr:
        video.ER1 = ord(c)
        video.wait_not_busy()

    # Draw color stripes with varying attributes.
    for row, (a, description) in enumerate(
        ALL_COLOR_ATTRIBUTES_80COLUMNS.items(),
        start=8,
    ):
        video.R6 = row
        video.R7 = 0x80  # column 1
        video.R3 = a
        video.ER1 = ord("@")
        video.R7 = 0x81  # column 3
        video.R3 = 0x11  # c1
        for c in description:
            video.ER1 = ord(c)
            video.wait_not_busy()

    reference = Screenshot.load(
        "test_colors_data/test_80columns_attributes_pat%02x.png" % pat_extra
    )
    if tgs_bgr == tgs_bir:
        video.expect_screenshot(reference, ChannelSet.RGBI)
    else:
        video.R1 = tgs_bir
        video.ER0 = 0x81
        video.wait_not_busy()
        video.expect_screenshot(reference, ChannelSet.RBI)
        video.R1 = tgs_bgr
        video.ER0 = 0x81
        video.wait_not_busy()
        video.expect_screenshot(reference, ChannelSet.RGB)


def test_80columns_cursor_generator(video: VideoChip):
    for pat_extra, pat_descr in ALL_PAT_CONFIGURATIONS_80COLUMNS.items():
        for mat_extra, mat_descr in ALL_MAT_CONFIGURATIONS.items():
            if mat_extra == 0:
                # skip the "no cursor" test case, because it's already covered
                # by test_80columns_attributes.
                continue

            for a, attr_descr in ALL_COLOR_ATTRIBUTES_80COLUMNS.items():
                yield f"pat{pat_extra:02x}mat{mat_extra:02x}a{a:x}", pat_extra, pat_descr, mat_extra, mat_descr, a, attr_descr


@test(parametric=test_80columns_cursor_generator)
def test_80columns_cursor(
    video: VideoChip,
    pat_extra: int,
    pat_descr: str,
    mat_extra: int,
    mat_descr: str,
    a: int,
    attr_descr: str,
):
    # Set 40 columns long mode.
    match video.chip_type:
        case VideoChipType.EF9345:
            tgs_bgr = 0xD0
            tgs_bir = 0xD0
            pat_base = 0x07
        case VideoChipType.TS9347:
            tgs_bgr = 0xC0
            tgs_bir = 0xD0
            pat_base = 0x03
    video.R1 = tgs_bgr
    video.ER0 = 0x81
    video.wait_not_busy()
    video.R1 = pat_base | pat_extra
    video.ER0 = 0x83
    video.wait_not_busy()

    # mat
    video.R1 = 0x02 | mat_extra  # green
    video.ER0 = 0x82
    video.wait_not_busy()

    # ror
    video.R1 = 0x08
    video.ER0 = 0x87
    video.wait_not_busy()

    # dor
    match video.chip_type:
        case VideoChipType.EF9345:
            video.R1 = 0x94
        case VideoChipType.TS9347:
            # See corresponding note in test_80columns_attributes.
            video.R1 = 0x14
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

    # Draw header.
    video.R0 = 0x51  # KRL with auto-increment.
    video.R3 = 0x11  # c1
    video.R6 = 0  # y
    video.R7 = 0  # x
    for c in pat_descr:
        video.ER1 = ord(c)
        video.wait_not_busy()

    # Draw test pattern.
    video.R6 = 8  # y
    video.R7 = 0  # x
    video.R3 = a * 0x11
    for c in " EXAMPLE ":
        video.ER1 = ord(c)
        video.wait_not_busy()
    video.R7 = 5  # x
    video.R3 = 0x11  # c1
    for c in attr_descr:
        video.ER1 = ord(c)
        video.wait_not_busy()

    # Draw cursor type description.
    video.R6 = 9  # y
    video.R7 = 0x81  # x
    video.R3 = 0x11  # c1
    for c in f"\x5E {mat_descr}"[:31]:
        video.ER1 = ord(c)
        video.wait_not_busy()

    # Position the cursor on the "A" of "EXAMPLE".
    video.R6 = 8  # y
    video.R7 = 0x81  # x

    reference = Screenshot.load(
        "test_colors_data/test_80columns_cursor_pat%02xmat%02xa%x.png"
        % (pat_extra, mat_extra, a)
    )
    if tgs_bgr == tgs_bir:
        video.expect_screenshot(reference, ChannelSet.RGBI)
    else:
        video.R1 = tgs_bir
        video.ER0 = 0x81
        video.wait_not_busy()
        video.expect_screenshot(reference, ChannelSet.RBI)
        video.R1 = tgs_bgr
        video.ER0 = 0x81
        video.wait_not_busy()
        video.expect_screenshot(reference, ChannelSet.RGB)


if __name__ == "__main__":
    test_main()
