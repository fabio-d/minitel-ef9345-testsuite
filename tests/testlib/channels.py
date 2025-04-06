from __future__ import annotations

import enum
import PIL.Image
import PIL.ImageChops


class ChannelSet(enum.Enum):
    """A set of channels among R (red), G (green), B (blue) and I (insert)."""

    # Values here correspond to flags 0bRGBI
    NONE = 0b0000
    I = 0b0001
    B = 0b0010
    BI = 0b0011
    G = 0b0100
    GI = 0b0101
    GB = 0b0110
    GBI = 0b0111
    R = 0b1000
    RI = 0b1001
    RB = 0b1010
    RBI = 0b1011
    RG = 0b1100
    RGI = 0b1101
    RGB = 0b1110
    RGBI = 0b1111

    def __and__(self, other: ChannelSet) -> ChannelSet:
        return ChannelSet(self.value & other.value)

    def __or__(self, other: ChannelSet) -> ChannelSet:
        return ChannelSet(self.value | other.value)

    def __invert__(self) -> ChannelSet:
        return ChannelSet(self.value ^ 0b1111)

    def __bool__(self) -> bool:
        return self != ChannelSet.NONE


def _generate_palette_image():
    img = PIL.Image.new("P", (1, 1))
    palette = []
    for color in ChannelSet:
        if color & ChannelSet.I:  # insert bit is set
            bright, dark = 0xFF, 0x00
        else:  # insert bit is not set
            bright, dark = 0xCC, 0x44
        r = bright if color & ChannelSet.R else dark
        g = bright if color & ChannelSet.G else dark
        b = bright if color & ChannelSet.B else dark
        palette.extend([r, g, b])
    img.putpalette(palette, "RGB")
    return img


PALETTE_IMAGE = _generate_palette_image()
"""
A an empty image whose palette contains all the possible colors.

All PNG screenshots manipulated by the tests are stored with this palette.

The index of the color corresponds to the corresponding ChannelSet value.
"""
