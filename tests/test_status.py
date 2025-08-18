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


if __name__ == "__main__":
    test_main()
