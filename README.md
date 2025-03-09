# EF9345/TS9347 test suite

This repository contains a test suite for emulators of the
[EF9345](https://en.wikipedia.org/wiki/Thomson_EF9345) and TS9347 video chips,
such as the one included in the [MAME project](https://www.mamedev.org/).

These video chips provided the graphic capabilities of many French
[Minitels](https://en.wikipedia.org/wiki/Minitel) in the 80s and 90s.

The tests in this repository can be run both against MAME (see
[emu_mame](emu_mame) subfolder) and against real chips, through a custom USB
adapter board (see [hw_devboard](hw_devboard) subfolder).

While it is possible (and, currently, expected) that some tests may not pass on
MAME, all the tests have been verified on real chips.

## License

Same as MAME, i.e. [GNU General Public License version 2](LICENSE) or later.
