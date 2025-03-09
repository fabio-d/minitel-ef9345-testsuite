#include "gpio.h"

#include <delay.h>
#include <fx2regs.h>

#define LED_D1 PA0        // On-board LED (0=on, 1=off)
#define LED_D2 PA1        // On-board LED (0=on, 1=off)
#define BUS_ALE PA3       // To AS of video chip
#define BUS_nRD PA4       // To DS of video chip
#define BUS_nWR PA5       // To R/nW of video chip
#define BUS_nCS PA6       // To nCS of video chip
#define BUS_ADDR_DATA IOD // To ADM pins of video chip

#define BUS_DRIVE(value)                                                       \
  do {                                                                         \
    BUS_ADDR_DATA = value;                                                     \
    OED = 0xff;                                                                \
  } while (false)

#define BUS_HIGH_Z()                                                           \
  do {                                                                         \
    OED = 0x00;                                                                \
  } while (false)

void gpio_setup(void) {
  // Set initial output values.
  BUS_ALE = 0;
  BUS_nRD = 1;
  BUS_nWR = 1;
  BUS_nCS = 1;

  // Set initial pin directions.
  OEA = 0b01111011;
  OED = 0x00;
}

void set_led1(bool on) {
  LED_D1 = !on;
}

void set_led2(bool on) {
  LED_D2 = !on;
}

uint8_t bus_read(uint8_t address) {
  BUS_ALE = 1;
  BUS_DRIVE(address);
  BUS_nCS = 0;
  SYNCDELAY2;
  BUS_ALE = 0;
  SYNCDELAY2;
  BUS_HIGH_Z();
  BUS_nCS = 1;
  SYNCDELAY2;
  BUS_nRD = 0;
  SYNCDELAY2;
  uint8_t result = BUS_ADDR_DATA;
  BUS_nRD = 1;
  SYNCDELAY2;
  return result;
}

void bus_write(uint8_t address, uint8_t data) {
  BUS_ALE = 1;
  BUS_DRIVE(address);
  BUS_nCS = 0;
  SYNCDELAY2;
  BUS_ALE = 0;
  SYNCDELAY2;
  BUS_nCS = 1;
  SYNCDELAY2;
  BUS_nWR = 0;
  BUS_DRIVE(data);
  SYNCDELAY2;
  BUS_nWR = 1;
  SYNCDELAY2;
  BUS_HIGH_Z();
}
