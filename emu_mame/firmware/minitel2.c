#include <8052.h>
#include <stdbool.h>
#include <stdint.h>

volatile __xdata __at(0x4020) uint8_t TS9347_REGISTERS[16];

// Initialize Timer 0 as free running, 16 bit.
static void timer_init(void) {
  TMOD = 0x01;
}

// Reset the overflow bit and restart counting from zero.
static void timer_start(void) {
  TR0 = 0;
  TL0 = TH0 = 0;
  TF0 = 0;
  TR0 = 1;
}

// Read the current value of Timer 0, clamped to UINT16_MAX on overflow.
static uint16_t timer_get(void) {
  uint8_t high, low;
  do {
    high = TH0;
    low = TL0;
  } while (high != TH0);

  if (TF0) {
    return UINT16_MAX;
  }

  return ((uint16_t)high << 8) | low;
}

// Initialize serial port (14400 8N1) using Timer 2.
static void serial_init(void) {
  RCAP2H = 0xFF;
  RCAP2L = 0xE1;
  T2CON = 0x34;
  SCON = 0x50;
  TI = 1;
}

static uint8_t serial_read(void) {
  while (!RI) {
  }
  uint8_t value = SBUF;
  RI = 0;
  return value;
}

static void serial_write(uint8_t value) {
  while (!TI) {
  }
  TI = 0;
  SBUF = value;
}

void main(void) {
  timer_init();
  serial_init();

  // Send an initial NOP command to put the chip in a known state.
  TS9347_REGISTERS[0x8] = 0x91;

  // For some reason the first character does not arrive correctly to MAME's
  // bitbanger socket. Let's send a first placeholder byte, wait a bit and
  // then send the real ready signal.
  serial_write(0);
  timer_start();
  while (timer_get() != UINT16_MAX) {
  }
  serial_write('!'); // signal that we're ready!

  while (true) {
    uint8_t cmd = serial_read();
    if (cmd >= 0x10 && cmd < 0x20) {
      serial_write(TS9347_REGISTERS[cmd & 0x0F]);
    } else if (cmd >= 0x20 && cmd < 0x30) {
      TS9347_REGISTERS[cmd & 0x0F] = serial_read();
    } else {
      // We've received an invalid command, let's "panic".
      while (1) {
        serial_write('!');
      }
    }
  }
}
