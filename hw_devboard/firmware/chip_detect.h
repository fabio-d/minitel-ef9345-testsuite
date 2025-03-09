#ifndef HW_DEVBOARD_FIRMWARE_CHIP_DETECT_H
#define HW_DEVBOARD_FIRMWARE_CHIP_DETECT_H

typedef enum {
  CHIP_UNKNOWN = 0,
  CHIP_EF9345 = 1,
  CHIP_TS9347 = 2,
} chip_type_t;

chip_type_t chip_detect(void);

#endif
