.module usb_descriptors
.area DSCR_AREA (CODE)

; Constants: USB device IDs.
USB_PID = 0x04b4
USB_VID = 0x0083

; Helper macro that is like .dw, but little-endian instead of big-endian.
.macro .dwle value
  .db (value) % 256
  .db (value) / 256
.endm

; Constants: Descriptor types.
DEVICE_DESCRIPTOR_TYPE = 1
CONFIGURATION_DESCRIPTOR_TYPE = 2
STRING_DESCRIPTOR_TYPE = 3
INTERFACE_DESCRIPTOR_TYPE = 4
ENDPOINT_DESCRIPTOR_TYPE = 5
DEVICE_QUALIFIER_TYPE = 6

; Constants: Lengths of fixed-length descriptor types.
DEVICE_DESCRIPTOR_LENGTH = 18
CONFIGURATION_DESCRIPTOR_LENGTH = 9
INTERFACE_DESCRIPTOR_LENGTH = 9
ENDPOINT_DESCRIPTOR_LENGTH = 7
DEVICE_QUALIFIER_LENGTH = 10

; Important: all the descriptors need to be aligned to even addresses so that
; they can be assigned to the SUDPTRx register.
.even                                   ; align to 2

; Device Descriptor.
_dev_dscr::
  .db DEVICE_DESCRIPTOR_LENGTH          ; bLength
  .db DEVICE_DESCRIPTOR_TYPE            ; bDescriptorType
  .dwle 0x0200                          ; bcdUSB = 2.00
  .db 0xff                              ; bDeviceClass = Vendor Specific
  .db 0xff                              ; bDeviceSubClass = Vendor Specific
  .db 0xff                              ; bDeviceProtocol = Vendor specific
  .db 64                                ; bMaxPacketSize0
  .dwle USB_PID                         ; idVendor
  .dwle USB_VID                         ; idProduct
  .dwle 0x0100                          ; bcdDevice = 1.00
  .db 0                                 ; iManufacturer
  .db 1                                 ; iProduct
  .db 0                                 ; iSerial
  .db 1                                 ; bNumConfigurations

.even                                   ; align to 2

; Configuration Descriptor (high-speed mode).
;
; It offers a single interface, with an isochronous EP to stream video data to
; the host if alternate config #1 is selected. In accordance to the USB 2.0
; specifications (section 5.6.3), the default config #0 does not require any
; isochronous bandwidth (in this case, by omitting the corresponding EP).
_highspd_dscr::
  .db CONFIGURATION_DESCRIPTOR_LENGTH   ; bLength
  .db CONFIGURATION_DESCRIPTOR_TYPE     ; bDescriptorType
  .dwle highspd_dscr_end-_highspd_dscr  ; wTotalLength
  .db 1                                 ; bNumInterfaces
  .db 1                                 ; bConfigurationValue
  .db 0                                 ; iConfiguration
  .db 0x80                              ; bmAttributes = Bus Powered, No Wakeup
  .db 100/2                             ; bMaxPower = 100 mA
; Configuration Descriptor -> Interface Descriptor (altif = 0).
  .db INTERFACE_DESCRIPTOR_LENGTH       ; bLength
  .db INTERFACE_DESCRIPTOR_TYPE         ; bDescriptorType
  .db 0                                 ; bInterfaceNumber
  .db 0                                 ; bAlternateSetting
  .db 0                                 ; bNumEndpoints
  .db 0xff                              ; bInterfaceClass = Vendor Specific
  .db 0xff                              ; bInterfaceSubClass = Vendor Specific
  .db 0xff                              ; bInterfaceProtocol = Vendor specific
  .db 0                                 ; iInterface
; Configuration Descriptor -> Interface Descriptor (altif = 1).
  .db INTERFACE_DESCRIPTOR_LENGTH       ; bLength
  .db INTERFACE_DESCRIPTOR_TYPE         ; bDescriptorType
  .db 0                                 ; bInterfaceNumber
  .db 1                                 ; bAlternateSetting
  .db 2                                 ; bNumEndpoints
  .db 0xff                              ; bInterfaceClass = Vendor Specific
  .db 0xff                              ; bInterfaceSubClass = Vendor Specific
  .db 0xff                              ; bInterfaceProtocol = Vendor specific
  .db 0                                 ; iInterface
; Configuration Descriptor -> Interface Descriptor -> Endpoint Descriptor.
  .db ENDPOINT_DESCRIPTOR_LENGTH        ; bLength
  .db ENDPOINT_DESCRIPTOR_TYPE          ; bDescriptorType
  .db 0x81                              ; bEndpointAddress = EP 1 IN
  .db 0x03                              ; bmAttributes = Interrupt
  .dwle 6                               ; wMaxPacketSize = 1x 6 bytes
  .db 5                                 ; bInterval
; Configuration Descriptor -> Interface Descriptor -> Endpoint Descriptor.
  .db ENDPOINT_DESCRIPTOR_LENGTH        ; bLength
  .db ENDPOINT_DESCRIPTOR_TYPE          ; bDescriptorType
  .db 0x82                              ; bEndpointAddress = EP 2 IN
  .db 0x05                              ; bmAttributes = Isochronous Async Data
  .dwle 0xc00                           ; wMaxPacketSize = 2x 1024 bytes
  .db 1                                 ; bInterval
highspd_dscr_end:

.even                                   ; align to 2

; Configuration Descriptor (full-speed mode).
;
; Usage of the video streaming capabilites is impossible in full-speed mode, due
; to the much lower transfer rate. Let's just advertise the same interface as
; the high-speed's default config, which does not offer the data transfer EPs.
_fullspd_dscr::
  .db CONFIGURATION_DESCRIPTOR_LENGTH   ; bLength
  .db CONFIGURATION_DESCRIPTOR_TYPE     ; bDescriptorType
  .dwle fullspd_dscr_end-_fullspd_dscr  ; wTotalLength
  .db 1                                 ; bNumInterfaces
  .db 1                                 ; bConfigurationValue
  .db 0                                 ; iConfiguration
  .db 0x80                              ; bmAttributes = Bus Powered, No Wakeup
  .db 100/2                             ; bMaxPower = 100 mA
; Configuration Descriptor -> Interface Descriptor.
  .db INTERFACE_DESCRIPTOR_LENGTH       ; bLength
  .db INTERFACE_DESCRIPTOR_TYPE         ; bDescriptorType
  .db 0                                 ; bInterfaceNumber
  .db 0                                 ; bAlternateSetting
  .db 0                                 ; bNumEndpoints
  .db 0xff                              ; bInterfaceClass = Vendor Specific
  .db 0xff                              ; bInterfaceSubClass = Vendor Specific
  .db 0xff                              ; bInterfaceProtocol = Vendor specific
  .db 0                                 ; iInterface
fullspd_dscr_end:

.even                                   ; align to 2

; Device Qualifier.
_dev_qual_dscr::
  .db DEVICE_QUALIFIER_LENGTH           ; bLength
  .db DEVICE_QUALIFIER_TYPE             ; bDescriptorType
  .dwle 0x0200                          ; bcdUSB = 2.00
  .db 0xff                              ; bDeviceClass = Vendor Specific
  .db 0xff                              ; bDeviceSubClass = Vendor Specific
  .db 0xff                              ; bDeviceProtocol = Vendor specific
  .db 64                                ; bMaxPacketSize0
  .db 1                                 ; bNumConfigurations
  .db 0                                 ; bReserved

.even                                   ; align to 2

; String descriptors.
_dev_strings::

; Index 0: The LANGID array.
str0:
  .db str0_end-str0                     ; bLength
  .db STRING_DESCRIPTOR_TYPE            ; bDescriptorType
  .dwle 0x0409                          ; LANGID for English (United States).
str0_end:

; Index 1: Used as iProduct in the Device descriptor.
str1:
  .db str1_end-str1                     ; bLength
  .db STRING_DESCRIPTOR_TYPE            ; bDescriptorType
  .dwle 'E'
  .dwle 'F'
  .dwle '9'
  .dwle '3'
  .dwle '4'
  .dwle '5'
  .dwle '/'
  .dwle 'T'
  .dwle 'S'
  .dwle '9'
  .dwle '3'
  .dwle '4'
  .dwle '7'
  .dwle 0x20 ; blank space
  .dwle 'V'
  .dwle 'i'
  .dwle 'd'
  .dwle 'e'
  .dwle 'o'
  .dwle 0x20 ; blank space
  .dwle 'A'
  .dwle 'd'
  .dwle 'a'
  .dwle 'p'
  .dwle 't'
  .dwle 'e'
  .dwle 'r'
str1_end:

; Marker for setupdat.c to stop searching further.
strSTOP:
  .db 0, 0
