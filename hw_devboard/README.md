# Hardware board: USB EF9345/TS9347 Video Adapter

This folder contains the schematics, firmware and host software for running the
test suite against real EF9345 and TS9347 chips using a custom board.

<p align="center">
<img src="pictures/main.jpg" alt="Image of two such boards, with the EF9345 and TS9347 video chips" width="50%" />
</p>

## Board description

The custom boards host the video chip (either EF9345P or TS9347CP/2R00), a 32
KiB RAM module for it to store the text buffers and a 74LS373N latch to
demultiplex RAM addresses. In addition, for the TS9347CP only, an LM393 and some
passives extract the video composite sync signal from the TS9347CP's analog Y
output.

The solder jumper pads (JP1 to JP9) on the back side of the board adapt some
internal connections to the connected video chip (the EF9345P and TS9347CP/2R00
are not pin compatible).

Jumpers JP11-JP14 make it possible to limit the available RAM size.

Bill of materials with links:

* U1: The video chip
  ([EF9345P](https://www.aliexpress.com/item/32905550985.html) or
  [TS9347CP/2R00](https://www.ebay.com/itm/281664411315)) and
  [its socket (40 pin variant)](https://www.aliexpress.com/item/1005006256010892.html).
* U2: [AS6C62256-55PCN](https://www.mouser.com/ProductDetail/913-AS6C62256-55PCN)
  SRAM and [its socket](https://www.mouser.com/ProductDetail/737-ICS-628-T).
* U3: [SN74LS373N](https://www.mouser.com/ProductDetail/595-SN74LS373N) and
  [its socket](https://www.mouser.com/ProductDetail/737-ICS-320-T).
* U4 (for the TS9347 only): LM393 and its socket (e.g. from
  [this kit](https://www.aliexpress.com/item/1005007032661721.html)).
* RV1 (for the TS9347 only): 200 kOhm RM065 potentiometer (e.g. from
  [this kit](https://www.aliexpress.com/item/1005006182414764.html)).
* R1 (for the TS9347 only): 220 kOhm resistor.
* R2 (for the TS9347 only): 4.7 kOhm resistor.
* C1 and C2 (for the TS9347 only): 10 uF electrolitic capacitors.
* 2.54 mm male and female pin headers (e.g. from
  [this kit](https://www.aliexpress.com/item/1005006034877497.html)).
* 3 (EF9345) or 4 (TS9347) 2.54 mm jumpers (e.g. from
  [this kit](https://www.aliexpress.com/item/4000583368141.html)).

In addition, the board itself needs to be mounted on the
[EZ-USB FX2LP development board](https://www.aliexpress.com/item/1005005100640836.html),
which provides the high-speed USB interface to both read/write the video chip's
registers and, most importantily, streaming the real-time video signal back to
the host computer at 12 MiB/s.

### EZ-USB FX2LP board pinout

| FX2 pin     | EF9345P pin | TS9347CP/2R00 pin | Description                  |
|-------------|-------------|-------------------|------------------------------|
| **Outputs:**                                                              ||||
| CTL0 (J2.16)| CLK (12)    | CLK (12)          | Video Chip Clock             |
| PA3 (J2.10) | AS (14)     | AS (14)           | Address Strobe (aka ALE)     |
| PA4 (J2.9)  | DS (15)     | DS (15)           | Data Strobe (aka ~RD)        |
| PA5 (J2.8)  | R/~W (16)   | R/~W (16)         | Read/Write (aka ~WR)         |
| PA6 (J2.7)  | ~CS (26)    | ~CS (20)          | Chip Select                  |
| **Inputs:**                                                               ||||
| PB0 (J1.15) | I (10)      | G (10)            | Video Signal Value (digital) |
| PB1 (J1.16) | R (9)       | R (9)             | Video Signal Value (digital) |
| PB2 (J1.17) | G (8)       | B (8)             | Video Signal Value (digital) |
| PB3 (J1.18) | B (7)       | not connected     | Video Signal Value (digital) |
| PB6 (J2.18) |             |                   | CTL0 loopback (for debug)    |
| PB7 (J2.17) | HVS/HS (5)  | Y (7) via LM393   | Video Signal Composite Sync  |
| **Bidirectional:**                                                        ||||
| PD0 (J2.5)  | AD0 (17)    | AD0 (17)          | Multiplexed Address/Data Bus |
| PD1 (J2.4)  | AD1 (18)    | AD1 (18)          | Multiplexed Address/Data Bus |
| PD2 (J2.3)  | AD2 (19)    | AD2 (19)          | Multiplexed Address/Data Bus |
| PD3 (J2.2)  | AD3 (21)    | AD3 (21)          | Multiplexed Address/Data Bus |
| PD4 (J2.1)  | AD4 (22)    | AD4 (22)          | Multiplexed Address/Data Bus |
| PD5 (J1.1)  | AD5 (23)    | AD5 (23)          | Multiplexed Address/Data Bus |
| PD6 (J1.2)  | AD6 (24)    | AD6 (24)          | Multiplexed Address/Data Bus |
| PD7 (J1.3)  | AD7 (25)    | AD7 (25)          | Multiplexed Address/Data Bus |

Note: When EZ-USB's J3 jumper is inserted, PA0 and PA1 control the on-board LEDs
(respectively D1 and D2). Our firmware reports what kind of chip it detected
through these LEDs: EF9345 = D1 on, TS9347 = D2 on, detection failed = both on.

### Schematic

[<img src="board_v1/plots/board_v1.svg">](board_v1/plots/board_v1.pdf)

## Customization

Before using the board, some customizations are necessary.

### Selecting the video chip

<p align="center">
<img src="pictures/solder_jumpers.jpg" alt="Solder jumpers JP1-JP9 in EF9345P configuration" height="300" />
</p>

JP1 to JP9 on the back side of the board need to be bridged with solder,
depending on the type of video chip to be tested:

* each JPx must be bridged to the left (i.e. by shorting pads 1 and 2) for the
  EF9345P, like in the picture above.
* each JPx must be bridged to the right (i.e. by shorting pads 2 and 3) for the
  TS9347CP/2R00, symmetrical to the picture above.

In addition, for the TS9347CP only, the RV1 potentiometer must be adjusted so
that its middle pin gives `TODO` V.

### Selecting the video RAM size

Provided neither long codes nor custom fonts are used, the EF9345 and TS9347 can
operate with as little as just 2 KiB of video RAM.

While the AS6C62256-55PCN RAM IC contains 32 KiB of RAM, it is possible to mask
some of its address lines through jumpers JP11-JP14 to make it appear smaller.
The following configurations are possible:

<table>
  <tr>
    <td align="center"><img width="60%" src="pictures/memory_2K.svg" /><br />2 K</td>
    <td align="center"><img width="60%" src="pictures/memory_4K.svg" /><br />4 K</td>
    <td align="center"><img width="60%" src="pictures/memory_8K.svg" /><br />8 K</td>
    <td align="center"><img width="60%" src="pictures/memory_16K.svg" /><br />16 K</td>
    <td align="center"><img width="60%" src="pictures/memory_32K.svg" /><br />32 K</td>
  </tr>
</table>

Note 1: JP14 is ignored and can be left unpopulated in the case of the EF9345
chip, as EF9345 only supports up to 16 KiB.

Note 2: current and future tests will assume that all the jumpers are connected
to the right (i.e. maximum possible RAM size).

### Getting 5 V power from the EZ-USB FX2LP development board

All the chips on our board (including, notably, the video chip) need to be
powered at 5 V. The USB power supply provided from the host would be suitable
(the USB bus provides power at exactly 5 V) but, unfortunately, no pin of the
EZ-USB FX2LP development board exposes the USB's 5 V line.

Therefore, in order to connect USB's 5 V to our board, we need to apply a small
mod to the EZ-USB FX2LP board by soldering and connecting a wire as shown in the
following images:

<p align="center">
<img src="pictures/mod_5V_bottom.svg" alt="Bottom side" width="40%" />
<img src="pictures/mod_5V_top.svg" alt="Top side" width="40%" />
</p>

Note: by soldering the wire in the way shown above, the power switch on the
front of the EZ-USB FX2LP board will be in control of our derived 5 V rail too.

### Supporting software

Prerequisites:

```shell
$ git submodule init && git submodule update  # to checkout firmware/fx2lib
$ sudo apt install build-essential cycfx2prog libusb-1.0-0-dev qt6-base-dev sdcc
```

Firmware for the FX2LP chip is provided in the `firmware` subdirectory and it
can be compiled and then loaded over USB into the board with:

```shell
$ cd hw_devboard/firmware
$ make
$ sudo cycfx2prog prg:build/firmware.ihx run
```

The above `cycfx2prog` command will load the firmware into the FX2LP's RAM and
execute it from there. It will not persist after power cycling.

The `host_connector_gui` program can then be started on the host:

```shell
$ cd hw_devboard/host_connector_gui
$ qmake6
$ make
$ sudo ./host_connector_gui
```

## Running the tests

After loading the firmware and opening the `host_connector_gui` program, select
*Device* &rarr; *Connect...* to locate the USB board, then *Device* &rarr;
*Enable TCP Server...* and confirm the default listen address `127.0.0.1:1234`.

Finally, run a test (e.g. `test_resolutions.py`) with:

```shell
$ cd ../tests
$ python3 test_resolutions.py --video-chip 127.0.0.1:1234
```

## Gallery

<p>
<img src="pictures/screenshot_40c.gif" alt="Screenshot of 40 columns mode" height="150" />
<img src="pictures/screenshot_80c.gif" alt="Screenshot of 40 columns mode" height="150" />
<img src="pictures/screenshot_colors.png" alt="Screenshot of colored bands" height="150" />
<img src="pictures/side_view.jpg" alt="A board seen from its left side" height="150" />
<img src="pictures/everything.jpg" alt="Populated and unpopulated boards" height="150" />
<img src="pictures/pcb.jpg" alt="The printed circuit" height="150" />
</p>
