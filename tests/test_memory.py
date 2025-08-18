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


# All the rows in a block.
# Note: row Y=1 is defined only in the EF9345 datasheet.
ALL_ROWS = [0, 1, *range(8, 32)]

# All the rows except Y=1, which is partial in odd blocks and its missing bytes
# are aliases of other rows' bytes.
ALL_FULL_ROWS = [0, *range(8, 32)]

# test_name -> (clear_start_x, clear_start_y, expected_cleared_start_y)
CLEAR_PAGE_PARAMETERS = {
    # Rows 2, 4 and 6 are all aliases of row 0, and 1, 3 and 7 alias to 1.
    "row0": (0, 0, 0),
    "row1": (0, 1, 0),  # will still clear row 0 because of its aliases
    "row6mid": (20, 6, 1),  # skip the first 20 columns of row 0 (alias 6)
    "row7mid": (20, 7, 8),  # skip the first 20 columns of row 1 (alias 7)
    # Any other starting position will eventually wrap around to row 8 and
    # clear all the rows >= 8:
    "row8": (0, 8, 8),
    "row8mid": (20, 8, 8),
    "row24mid": (20, 24, 8),
    "row31": (0, 31, 8),
}


@test(parametric=CLEAR_PAGE_PARAMETERS)
def test_clear_page16(
    video: VideoChip,
    clear_start_x: int,
    clear_start_y: int,
    expected_cleared_start_y: int,
):
    # TGS
    video.R1 = 0xD0
    video.ER0 = 0x81
    video.wait_not_busy()

    # PAT
    video.R1 = 0x00
    video.ER0 = 0x83
    video.wait_not_busy()

    # ROR
    video.R1 = 0x08
    video.ER0 = 0x87
    video.wait_not_busy()

    # DOR
    video.R1 = 0x00
    video.ER0 = 0x84
    video.wait_not_busy()

    # Write a known value at the first column of each row in district 0.
    match video.chip_type:
        case VideoChipType.EF9345:
            krg_or_tsm = 0x02  # KRG
        case VideoChipType.TS9347:
            krg_or_tsm = 0x60  # TSM
    video.R0 = krg_or_tsm  # KRG/TSM
    for y in ALL_FULL_ROWS:
        video.R6 = y
        # Write into the first two blocks.
        video.R1 = (0 << 6) | y
        video.R2 = (1 << 6) | y
        video.ER7 = 0  # x=0, block=0
        video.wait_not_busy()
        # Write into the last two blocks.
        video.R1 = (2 << 6) | y
        video.R2 = (3 << 6) | y
        video.ER7 = 0x40  # x=0, block=2
        video.wait_not_busy()

    # Begin clearing with different known values, staring with the cursor at the
    # given position. Note: only the first two blocks will be affected.
    video.R1 = 1
    video.R2 = 2
    video.R6 = clear_start_y
    video.R7 = clear_start_x
    video.ER0 = 0x07  # CLG/CLS
    assert video.R0 & 0x80  # busy flag is set
    time.sleep(0.1)  # leave the command running for a while
    assert video.R0 & 0x80  # busy flag is still set
    video.ER0 = 0x91  # NOP to stop it.
    video.wait_not_busy()

    # While the command was running, the Y pointer (R6) will have wrapped many
    # times from 31 to 8.
    assert 8 <= video.R6 <= 31

    # Read the first columns back, verifying that all of them have been cleared.
    video.R0 = krg_or_tsm | 0x08  # KRG/TSM + read
    for y in ALL_FULL_ROWS:
        video.R6 = y
        # Verify that the first two blocks have been affected.
        video.ER7 = 0  # x=0, block=0
        video.wait_not_busy()
        if y >= expected_cleared_start_y:
            assert video.R1 == 1
            assert video.R2 == 2
        else:
            assert video.R1 == (0 << 6) | y
            assert video.R2 == (1 << 6) | y
        # Verify that the last two blocks have *not* been affected.
        video.ER7 = 0x40  # x=0, block=2
        video.wait_not_busy()
        assert video.R1 == (2 << 6) | y
        assert video.R2 == (3 << 6) | y


@test(parametric=CLEAR_PAGE_PARAMETERS)
def test_clear_page24(
    video: VideoChip,
    clear_start_x: int,
    clear_start_y: int,
    expected_cleared_start_y: int,
):
    # TGS
    video.R1 = 0xD0
    video.ER0 = 0x81
    video.wait_not_busy()

    # PAT
    video.R1 = 0x00
    video.ER0 = 0x83
    video.wait_not_busy()

    # ROR
    video.R1 = 0x08
    video.ER0 = 0x87
    video.wait_not_busy()

    # DOR
    video.R1 = 0x00
    video.ER0 = 0x84
    video.wait_not_busy()

    # Write a known value at the first column of each row in district 0.
    # This will touch three out of the four blocks in district 0.
    video.R0 = 0x00  # KRF/TLM
    video.R7 = 0  # x
    for y in ALL_ROWS:
        video.R1 = (1 << 6) | y
        video.R2 = (2 << 6) | y
        video.R3 = (3 << 6) | y
        video.ER6 = y  # y
        video.wait_not_busy()

    # For the remaining block of district 0, write a canary value in each row.
    video.R0 = 0x30  # OCT/TBM
    video.R7 = 0 | (3 << 6)  # x, block=3
    for y in ALL_FULL_ROWS:
        video.R1 = y ^ 0xFF
        video.ER6 = y  # y
        video.wait_not_busy()

    # Begin clearing with different known values, staring with the cursor at the
    # given position.
    video.R1 = 1
    video.R2 = 2
    video.R3 = 3
    video.R6 = clear_start_y
    video.R7 = clear_start_x
    video.ER0 = 0x05  # CLF/CLL
    assert video.R0 & 0x80  # busy flag is set
    time.sleep(0.1)  # leave the command running for a while
    assert video.R0 & 0x80  # busy flag is still set
    video.ER0 = 0x91  # NOP to stop it.
    video.wait_not_busy()

    # While the command was running, the Y pointer (R6) will have wrapped many
    # times from 31 to 8.
    assert 8 <= video.R6 <= 31

    # Read the first columns back, verifying that all of them have been cleared.
    video.R0 = 0x08  # KRF/TLM + read
    video.R7 = 0  # x
    for y in ALL_ROWS:
        video.ER6 = y  # y
        video.wait_not_busy()
        if y >= expected_cleared_start_y:
            assert video.R1 == 1, (y, video.R1, video.R2, video.R3)
            assert video.R2 == 2, (y, video.R1, video.R2, video.R3)
            assert video.R3 == 3, (y, video.R1, video.R2, video.R3)
        else:
            assert video.R1 == (1 << 6) | y
            assert video.R2 == (2 << 6) | y
            assert video.R3 == (3 << 6) | y

    # Verify that the canary values were not affected.
    video.R0 = 0x38  # OCT/TBM + read
    video.R7 = 0 | (3 << 6)  # x, block=3
    for y in ALL_FULL_ROWS:
        video.ER6 = y  # y
        video.wait_not_busy()
        assert video.R1 == y ^ 0xFF


if __name__ == "__main__":
    test_main()
