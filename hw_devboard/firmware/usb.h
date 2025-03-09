#ifndef HW_DEVBOARD_FIRMWARE_USB_H
#define HW_DEVBOARD_FIRMWARE_USB_H

#include <autovector.h> // Interrupt declarations must be present in main file.

// Set by the SUDAV interrupt handler to ask the main loop to call
// "handle_setupdata" to handle a USB setup packet.
extern volatile __bit got_sud;

void disable_all_usb_endpoints(void);

// Note: clearing *all* the WORDWIDE flags releases port D and makes it behave
// as a regular GPIO.
void unset_all_wordwide_flags(void);

void start_usb_streaming(void);

#endif
