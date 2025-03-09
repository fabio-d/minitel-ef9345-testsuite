#ifndef VIDEOCHIP_H
#define VIDEOCHIP_H

enum VideoChipType {
  EF9345,
  TS9347,
};

// For each function, the corresponding mask in the incoming samples (or 0 if
// not available).
struct VideoChipChannelMapping {
  auto operator<=>(const VideoChipChannelMapping &) const = default;

  char red_mask = 0;
  char green_mask = 0;
  char blue_mask = 0;
  char insert_mask = 0;
  char hvs_mask = 0;
};

enum VideoChipMode {
  VIDEO_MODE_40_COLUMNS,
  VIDEO_MODE_80_COLUMNS,
};

enum VideoChipRegister {
  REG_R0 = 0,
  REG_R1 = 1,
  REG_R2 = 2,
  REG_R3 = 3,
  REG_R4 = 4,
  REG_R5 = 5,
  REG_R6 = 6,
  REG_R7 = 7,
  REG_ER0 = 8 | 0,
  REG_ER1 = 8 | 1,
  REG_ER2 = 8 | 2,
  REG_ER3 = 8 | 3,
  REG_ER4 = 8 | 4,
  REG_ER5 = 8 | 5,
  REG_ER6 = 8 | 6,
  REG_ER7 = 8 | 7,
};

#endif
