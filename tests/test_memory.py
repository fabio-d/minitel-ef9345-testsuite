import time
from pathlib import Path
from testlib import *


@test(parametric={"b%dy%d" % (b, y): (b, y) for b in [0, 1] for y in range(32)})
def test_address_transcoding(video: VideoChip, tested_b: int, tested_y: int):
    # Set TGS to ensure the chip is in a valid video mode.
    match video.chip_type:
        case VideoChipType.EF9345:
            video.R1 = 0x10
        case VideoChipType.TS9347:
            video.R1 = 0x00
    video.ER0 = 0x81
    video.wait_not_busy()

    # Set every byte in blocks 0 and 1 to zero.
    video.R1 = 0
    video.R2 = 0
    video.R6 = 0  # y
    video.R7 = 0  # block, x
    video.ER0 = 0x07  # CLG/CLS
    assert video.R0 & 0x80  # busy flag is set
    time.sleep(0.1)  # leave the command running for a while
    assert video.R0 & 0x80  # busy flag is still set
    video.ER0 = 0x91  # NOP to stop it.
    video.wait_not_busy()

    # Fill row "tested_y" of block "tested_b" with unique values.
    video.R0 = 0x31  # OCT/TBM with auto-increment
    video.R6 = tested_y
    video.R7 = (0x80 if (tested_b & 1) else 0) | (0x40 if (tested_b & 2) else 0)
    for x in range(40):
        video.ER1 = 0x30 + x
        video.wait_not_busy()

    # Read back all of blocks 0 and 1.
    video.R0 = 0x39  # OCT/TBM (read) with auto-increment
    output = "B  Y DATA...\n"
    for b in [0, 1]:
        for y in range(32):
            output += "%d %2d" % (b, y)
            video.R6 = y
            r7_base = (0x80 if (b & 1) else 0) | (0x40 if (b & 2) else 0)
            for x in range(40):
                video.ER7 = r7_base | x
                video.wait_not_busy()
                output += " %02x" % video.R1
            output += "\n"

    # Compare against the expected memory dump.
    reference_path = Path(
        "test_memory_data/test_address_transcoding_b%dy%d.txt"
        % (tested_b, tested_y)
    )
    assert reference_path.read_text() == output


if __name__ == "__main__":
    test_main()
