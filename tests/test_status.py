import time
from testlib import *


@test()
def test_not_busy(video: VideoChip):
    # tgs
    video.R1 = 0xD0
    video.ER0 = 0x81
    video.wait_not_busy()

    # pat
    video.R1 = 0x00
    video.ER0 = 0x83
    video.wait_not_busy()

    video.ER0 = 0x91  # NOP
    video.wait_not_busy()

    # Check the BUSY flag as often as possible. Given that no command is
    # pending, it should stay to zero all the time.
    start = time.monotonic_ns()
    while time.monotonic_ns() - start < 500000000:  # 500 ms
        assert (video.R0 & 0x80) == 0


# Test NOP and its aliases.
@test(parametric={f"NOP{cmd:02x}": (cmd,) for cmd in range(0x90, 0x94)})
def test_status_nop(video: VideoChip, cmd: int):
    # Set TGS to ensure the chip is in a valid video mode.
    match video.chip_type:
        case VideoChipType.EF9345:
            video.R1 = 0x10
        case VideoChipType.TS9347:
            video.R1 = 0x00
    video.ER0 = 0x81
    video.wait_not_busy()

    video.R1 = 0x11
    video.R2 = 0x22
    video.R3 = 0x33
    video.R4 = 0x44
    video.R5 = 0x55
    video.R6 = 0x66
    video.R7 = 0x77

    video.ER0 = cmd  # NOP
    video.wait_not_busy()

    assert video.R1 == 0x11
    assert video.R2 == 0x22
    assert video.R3 == 0x33
    assert video.R4 == 0x44
    assert video.R5 == 0x55
    assert video.R6 == 0x66
    assert video.R7 == 0x77


def test_status_vsync_generator(video: VideoChip):
    for cmd in range(0x94, 0x9F + 1):
        if 0x98 <= cmd <= 0x9B:
            yield f"VSM{cmd:02x}", cmd, False
        else:
            yield f"VRM{cmd:02x}", cmd, True


# Test VRM and VSM and their aliases.
@test(parametric=test_status_vsync_generator)
def test_status_vsync(video: VideoChip, cmd: int, expect_vsync: bool):
    # Set TGS to ensure the chip is in a valid video mode. On the TS9347,
    # select the internally generated VSYNC as the service sync source.
    match video.chip_type:
        case VideoChipType.EF9345:
            video.R1 = 0x10
        case VideoChipType.TS9347:
            video.R1 = 0x04
    video.ER0 = 0x81
    video.wait_not_busy()

    # Put the mask in the opposite state first, so that we know the starting
    # state and can observe the effect of the command under test.
    video.ER0 = 0x99 if expect_vsync else 0x95  # VSM / VRM
    video.wait_not_busy()

    video.ER0 = cmd
    video.wait_not_busy()

    # Sample the VSYNC bit in the STATUS register as often as possible for 5
    # seconds.
    zeros = total = 0
    end = time.monotonic() + 5
    while time.monotonic() < end:
        if not (video.R0 & 0x04):
            zeros += 1
        total += 1

    if expect_vsync:
        duty_cycle = zeros / total
        # Expected: ~2/312 = 0.64% (2 lines per frame)
        assert 0 < duty_cycle < 0.10
    else:
        assert zeros == total  # VSYNC shold never be asserted


if __name__ == "__main__":
    test_main()
