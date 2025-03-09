#include "chip_detect.h"
#include "gpio.h"
#include "usb.h"

#include <delay.h>
#include <fx2macros.h>
#include <fx2regs.h>
#include <setupdat.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>

static struct {
  uint8_t red_mask;
  uint8_t green_mask;
  uint8_t blue_mask;
  uint8_t insert_mask;
  uint8_t hvs_mask;
  uint8_t mode;
} status_bytes;
static __bit status_bytes_changed;

static chip_type_t chip_type;
static uint8_t current_R0;

static void wait_ep0_not_busy(void) {
  while (EP0CS & bmEPBUSY) {
  }
}

static void decode_status_bytes(uint8_t tgs) {
  if (chip_type == CHIP_TS9347) {
    if (tgs & (1 << 5)) {
      status_bytes.red_mask = 0;
      status_bytes.green_mask = 0;
      status_bytes.blue_mask = 0;
      if (tgs & (1 << 4)) {
        status_bytes.insert_mask = 1u << 0;
      } else {
        status_bytes.insert_mask = 0;
      }
    } else {
      status_bytes.red_mask = 1u << 1;
      status_bytes.blue_mask = 1u << 2;
      if (tgs & (1 << 4)) {
        status_bytes.green_mask = 0;
        status_bytes.insert_mask = 1u << 0;
      } else {
        status_bytes.green_mask = 1u << 0;
        status_bytes.insert_mask = 0;
      }
    }
  } else {
    status_bytes.red_mask = 1u << 1;
    status_bytes.green_mask = 1u << 2;
    status_bytes.blue_mask = 1u << 3;
    status_bytes.insert_mask = 1u << 0;
  }
  status_bytes.hvs_mask = 1u << 7;

  // Note: this condition works for both chips.
  status_bytes.mode = (tgs & 0x80) == 0 ? 1 : 0;

  status_bytes_changed = true;
}

static bool do_regaccess(bool is_in) {
  uint8_t regnum = SETUPDAT[2] & 0xF; // i.e. lsb of SETUP_VALUE()
  uint8_t value = SETUPDAT[3];        // i.e. msb of SETUP_VALUE()

  // Read requests will need to emit 1 byte of output data.
  if (SETUP_LENGTH() != (is_in ? 1 : 0)) {
    return false;
  }

  // If R0 is being modified, update our shadow copy.
  if (!is_in && (regnum & 0x7) == 0) {
    current_R0 = value;
  }

  // If we are about to ask the chip to set TGS, derive the new status bytes
  // from the value we are about to set.
  if ((regnum & 0x8) != 0 && current_R0 == 0x81) {
    if (!is_in && (regnum & 0x7) == 1) {
      decode_status_bytes(value);
    } else {
      // Ensure the chip is idle by executing a NOP command.
      bus_write(0x28, 0x91);
      SYNCDELAY16;

      // Read the current value of R1.
      uint8_t new_tgs_value = bus_read(0x21);
      decode_status_bytes(new_tgs_value);

      // Restore R0.
      bus_write(0x20, current_R0);
    }
  }

  // Execute the requested command.
  if (is_in) {
    uint8_t result = bus_read(0x20 | regnum);
    wait_ep0_not_busy();
    EP0BUF[0] = result;
    EP0BCH = 0;
    EP0BCL = 1;
  } else {
    bus_write(0x20 | regnum, value);
  }

  return true;
}

static bool do_status(void) {
  if (SETUP_LENGTH() != sizeof(status_bytes) + 1) {
    return false; // invalid request
  }

  wait_ep0_not_busy();

  // Fill the buffer with the current status bytes...
  memcpy(EP0BUF, &status_bytes, sizeof(status_bytes));

  // ...and append the chip type too.
  EP0BUF[sizeof(status_bytes)] = chip_type;

  EP0BCH = 0;
  EP0BCL = sizeof(status_bytes) + 1;

  return true;
}

BOOL handle_vendorcommand(BYTE cmd) {
  // Only accept the request if:
  // - bmRequestType has Type == Vendor and Recipient == Interface
  // - wIndex (target interface number) == 0
  if ((SETUP_TYPE & 0x7f) != 0x41 || SETUP_INDEX() != 0) {
    return false;
  }

  // Read the bmRequestType top bit to determine if the direction is
  // device-to-host (true) or host-to-device (false).
  bool is_in = (SETUP_TYPE & 0x80) != 0;

  // Dispatch according to cmd (bRequest).
  if (cmd == 0x10) {
    return do_regaccess(is_in);
  } else if (cmd == 0x11 && is_in) {
    return do_status();
  } else {
    return false;
  }
}

void main(void) {
  // Bring some USB features from their defaults to a disabled state.
  disable_all_usb_endpoints();
  unset_all_wordwide_flags();

  // Configure I/O pins.
  gpio_setup();

  // Disconnect and reconnect, presenting our custom USB descriptors instead of
  // the EZ-USB's defaults.
  RENUMERATE();

  // Start continuously streaming readouts of port B to the host.
  start_usb_streaming();

  // Configure and enable EP1IN as an interrupt endpoint.
  EP1INCFG = bmVALID | bmTYPE1 | bmTYPE0;
  EP1INCS = 0;

  // Enable interrupts.
  USE_USB_INTS();
  ENABLE_SUDAV();
  ENABLE_HISPEED();
  ENABLE_USBRESET();
  EA = 1;

  // Send a NOP command at power-on as recommended by the TS9347 datasheet.
  bus_write(0x28, 0x91);
  SYNCDELAY16;

  // Detect the video chip type.
  chip_type = chip_detect();

  // Read TGS and initialize our shadow R0 tracking and the status bytes.
  bus_write(0x28, 0x89);
  current_R0 = 0x89;
  SYNCDELAY16;
  SYNCDELAY16;
  SYNCDELAY16;
  SYNCDELAY16;
  decode_status_bytes(bus_read(0x21));

  switch (chip_type) {
  case CHIP_EF9345:
    set_led1(true);
    set_led2(false);
    break;
  case CHIP_TS9347:
    set_led1(false);
    set_led2(true);
    break;
  default:
    set_led1(true);
    set_led2(true);
    break;
  }

  while (true) {
    if (got_sud) {
      got_sud = false;
      handle_setupdata();
    }

    // Send status bytes updates through EP1IN as soon as possible.
    if (status_bytes_changed && !(EP1INCS & bmEPBUSY)) {
      status_bytes_changed = false;
      memcpy(EP1INBUF, &status_bytes, sizeof(status_bytes));
      EP1INBC = sizeof(status_bytes);
    }
  }
}
