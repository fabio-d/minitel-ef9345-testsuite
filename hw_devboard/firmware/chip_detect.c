#include "chip_detect.h"

#include "gpio.h"

#include <delay.h>
#include <stdbool.h>

// A blank glyph.
static uint8_t glyph_blank[10] = {
    // clang-format off
    0b00000000,
    0b00000000,
    0b00000000,
    0b00000000,
    0b00000000,
    0b00000000,
    0b00000000,
    0b00000000,
    0b00000000,
    0b00000000,
    // clang-format on
};

// G10 character 0x19.
static uint8_t glyph_mosaic_19[10] = {
    // clang-format off
    0b00001110,
    0b00001110,
    0b00000000,
    0b11100000,
    0b11100000,
    0b11100000,
    0b00000000,
    0b00001110,
    0b00001110,
    0b00000000,
    // clang-format on
};

// Reads the requested glyphs from the video chip and compares it to the given
// template.
static bool read_and_test_glyph(uint8_t b, uint8_t c,
                                const char reference[10]) {
  uint8_t r6 = ((b & 0x04) ? 0x20 : 0x00) | ((c & 0x7c) >> 2);
  uint8_t r7 = ((b & 0x01) ? 0x80 : 0) | ((b & 0x02) ? 0x40 : 0) | (c & 0x03);

  bus_write(0x20, 0x88); // IND read ROM
  bus_write(0x26, r6);
  for (uint8_t scanline = 0; scanline < 10; ++scanline) {
    bus_write(0x2F, r7 | (scanline << 2));
    SYNCDELAY16;
    SYNCDELAY16;
    SYNCDELAY16;
    SYNCDELAY16;

    if (bus_read(0x21) != reference[scanline]) {
      return false;
    }
  }

  return true;
}

chip_type_t chip_detect(void) {
  // The internal ROM cannot be read on the EF9345 if no valid video mode is
  // set: ensure a valid value is set by clearing the top two TGS bits.
  bus_write(0x28, 0x89);
  SYNCDELAY16;
  SYNCDELAY16;
  SYNCDELAY16;
  SYNCDELAY16;
  uint8_t tgs = bus_read(0x21);
  bus_write(0x21, tgs & 0x3F);
  bus_write(0x28, 0x81);
  SYNCDELAY16;
  SYNCDELAY16;
  SYNCDELAY16;
  SYNCDELAY16;

  // Validate that a valid chip is connected by reading character 0x19 from the
  // G10 character set. It has a non-trivial glyph (which makes it reliably
  // distinguishable from electrical noise) and it is the same in both chips.
  if (!read_and_test_glyph(2, 0x19, glyph_mosaic_19)) {
    return CHIP_UNKNOWN;
  }

  // Read character 0x10 from G11 (EF9345) / GOE (TS9347):
  // - The EF9345 will respond with a blank glyph.
  // - The TS9347 will respond with an accented i.
  return read_and_test_glyph(3, 0x10, glyph_blank) ? CHIP_EF9345 : CHIP_TS9347;
}
