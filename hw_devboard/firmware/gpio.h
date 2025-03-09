#ifndef HW_DEVBOARD_FIRMWARE_GPIO_H
#define HW_DEVBOARD_FIRMWARE_GPIO_H

#include <stdbool.h>
#include <stdint.h>

void gpio_setup(void);

// On-board LED control.
void set_led1(bool on);
void set_led2(bool on);

// Video chip bus I/O (bitbanged).
uint8_t bus_read(uint8_t address);
void bus_write(uint8_t address, uint8_t data);

#endif
