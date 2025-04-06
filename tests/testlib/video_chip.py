from __future__ import annotations

import base64
import enum
import io
import socket
import time
import PIL.Image

from .channels import ChannelSet
from .image_utils import test_images_equal, vertical_concat
from .screenshot import Screenshot


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

    def expect_screenshot(self, reference: Screenshot, channels: ChannelSet):
        matcher = reference.create_matcher(channels)

        prev_header_and_size = channels = None  # not known yet
        unique_stream_images = []

        for i in range(15):  # give up after 15 frames
            if i != 0:
                time.sleep(0.1)  # short delay
            else:
                time.sleep(0.5)  # longer delay before the initial frame

            # Request a screenshot:
            self._writer.write("SCREENSHOT?\n")
            self._writer.flush()

            # Read the header and the image payload.
            header = self._reader.readline()
            data = base64.b64decode(self._reader.readline())
            image = PIL.Image.open(io.BytesIO(data))

            # Ensure uniformity.
            if prev_header_and_size is not None:
                assert (header, image.size) == prev_header_and_size
            else:
                prev_header_and_size = (header, image.size)
                channels = ChannelSet.NONE
                if "R" in header:
                    channels |= ChannelSet.R
                if "G" in header:
                    channels |= ChannelSet.G
                if "B" in header:
                    channels |= ChannelSet.B
                if "I" in header:
                    channels |= ChannelSet.I

            # Store each unique frame we see in the stream.
            if len(unique_stream_images) == 0 or not test_images_equal(
                unique_stream_images[-1], image
            ):
                unique_stream_images.append(image)

            if matcher.advance(image, channels):
                return

        vertical_concat(*unique_stream_images).show("actual_uniq")
        vertical_concat(*reference.images).show("reference")
        raise AssertionError("The screenshot did not match")

    def screenshot(self, n_frames: int = 1):
        assert n_frames >= 1

        prev_header_and_size = None  # not known yet
        images = []

        for i in range(n_frames):
            if i != 0:
                time.sleep(0.1)  # short delay
            else:
                time.sleep(0.5)  # longer delay before the initial frame

            # Request a screenshot:
            self._writer.write("SCREENSHOT?\n")
            self._writer.flush()

            # Read the header and the image payload.
            header = self._reader.readline()
            data = base64.b64decode(self._reader.readline())
            image = PIL.Image.open(io.BytesIO(data))

            # Ensure uniformity.
            if prev_header_and_size is not None:
                assert (header, image.size) == prev_header_and_size
            else:
                prev_header_and_size = (header, image.size)

            images.append(image)

        # Pack into a Screenshot instance.
        channels = ChannelSet.NONE
        if "R" in header:
            channels |= ChannelSet.R
        if "G" in header:
            channels |= ChannelSet.G
        if "B" in header:
            channels |= ChannelSet.B
        if "I" in header:
            channels |= ChannelSet.I
        return Screenshot(images, channels)

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
