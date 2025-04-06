import time
from collections import defaultdict
import PIL.Image
from testlib import *

# All the PAT bits that may affect how color and insert channels are rendered.
ALL_PAT_CONFIGURATIONS = {  # pat_value -> description
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

# All the attributes that affect the output color and insert channels.
# Note: The TS9347 has an extra attribute (i2 - stored in B), that is only
# meaningful if the insert mode is "Boxing and Inlay" (see PAT) and i1 == 1.
ALL_COLOR_ATTRIBUTES_EF9345 = {  # (a, b) -> description
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
ALL_COLOR_ATTRIBUTES_TS9347 = {  # (a, b) -> description
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

# All the MAT bits that may affect how the cursor is rendered.
ALL_MAT_CONFIGURATIONS = {  # mat_value => description
    0x00: "No cursor",
    0x40: "FixedComplemented",
    0x50: "FlashComplemented",
    0x60: "FixedUnderlined",
    0x70: "FlashUnderline",
}


def test_40columns_attributes_generator(video: VideoChip):
    for pat_extra, pat_descr in ALL_PAT_CONFIGURATIONS.items():
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
            all_color_attributes = ALL_COLOR_ATTRIBUTES_EF9345
        case VideoChipType.TS9347:
            all_color_attributes = ALL_COLOR_ATTRIBUTES_TS9347
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


if __name__ == "__main__":
    test_main()
