from __future__ import annotations

import base64
import enum
import io
import socket
import time
from typing import Tuple
import PIL.Image


class VideoChipType(enum.Enum):
    EF9345 = "EF9345"
    TS9347 = "TS9347"


class _VideoChipRegisterDescriptor:
    def __init__(self, regnum: int, execute: bool) -> None:
        self._regnum = regnum
        self._execute = execute

    def __get__(self, obj: VideoChip, _objtype: type = None) -> int:
        return obj.read_register(self._regnum, self._execute)

    def __set__(self, obj: VideoChip, value: int):
        obj.write_register(self._regnum, value, self._execute)


class VideoChip:
    R0 = _VideoChipRegisterDescriptor(0, False)
    R1 = _VideoChipRegisterDescriptor(1, False)
    R2 = _VideoChipRegisterDescriptor(2, False)
    R3 = _VideoChipRegisterDescriptor(3, False)
    R4 = _VideoChipRegisterDescriptor(4, False)
    R5 = _VideoChipRegisterDescriptor(5, False)
    R6 = _VideoChipRegisterDescriptor(6, False)
    R7 = _VideoChipRegisterDescriptor(7, False)
    ER0 = _VideoChipRegisterDescriptor(0, True)
    ER1 = _VideoChipRegisterDescriptor(1, True)
    ER2 = _VideoChipRegisterDescriptor(2, True)
    ER3 = _VideoChipRegisterDescriptor(3, True)
    ER4 = _VideoChipRegisterDescriptor(4, True)
    ER5 = _VideoChipRegisterDescriptor(5, True)
    ER6 = _VideoChipRegisterDescriptor(6, True)
    ER7 = _VideoChipRegisterDescriptor(7, True)

    def __init__(self, host: str, port: int):
        self._sk = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP
        )
        self._sk.connect((host, port))
        self._sk.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self._reader = self._sk.makefile("r")
        self._writer = self._sk.makefile("w")

    @property
    def chip_type(self) -> VideoChipType:
        self._writer.write("TYPE?\n")
        self._writer.flush()
        return VideoChipType(self._reader.readline().strip())

    def rgb_screenshot(self) -> PIL.Image.Image:
        self._writer.write("RGB?\n")
        self._writer.flush()
        data = base64.b64decode(self._reader.readline())
        return PIL.Image.open(io.BytesIO(data))

    def flashing_rgb_screenshot(
        self,
    ) -> Tuple[PIL.Image.Image, PIL.Image.Image]:
        first = self.rgb_screenshot()
        for i in range(20):
            time.sleep(0.1)
            second = self.rgb_screenshot()
            if first.tobytes() != second.tobytes():
                break
        if first.tobytes() > second.tobytes():
            first, second = second, first  # make output order predictable
        return first, second

    def read_register(self, regnum: int, execute: bool) -> int:
        assert regnum < 8

        if not execute:
            self._writer.write("R%d?\n" % regnum)
        else:
            self._writer.write("ER%d?\n" % regnum)
        self._writer.flush()
        return int(self._reader.readline(), 16)

    def write_register(self, regnum: int, value: bool, execute: bool) -> int:
        assert regnum < 8
        assert 0 <= value < 256

        if not execute:
            self._writer.write("R%d=%02X\n" % (regnum, value))
        else:
            self._writer.write("ER%d=%02X\n" % (regnum, value))
        self._writer.flush()

    def wait_not_busy(self):
        while self.R0 & 0x80:
            pass  # keep waiting
