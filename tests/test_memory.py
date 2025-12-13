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


def test_clear_page16_generator(video: VideoChip):
    match video.chip_type:
        case VideoChipType.EF9345:
            commands = [0x07]
        case VideoChipType.TS9347:
            # On the TS9347, test the two undocumented aliases of CLS too.
            commands = [0x07, 0x65, 0x67]
    for name, args in CLEAR_PAGE_PARAMETERS.items():
        for cmd in commands:
            yield f"{name}/{cmd:02x}", cmd, *args


@test(parametric=test_clear_page16_generator)
def test_clear_page16(
    video: VideoChip,
    cmd: int,
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
    video.ER0 = cmd  # CLG/CLS
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


# Command types:
# - "24"  : 40 characters - 24 bits
# - "16"  : 40 characters - 16 bits
# - "16W" : 40 characters - 16 bits that behaves like "24" on reads
# - "8"   : 80 characters - 8 bits
# - "12"  : 80 characters - 12 bits
# - "B"   : Direct byte access
#
# Known undocumented aliases are tested too.
def test_memory_access_generator(video: VideoChip):
    match video.chip_type:
        case VideoChipType.EF9345:
            yield "KRF00", 0x00, "24", False
            yield "KRG02", 0x02, "16W", False
            for cmd in [0x40, 0x42, 0x44, 0x46]:
                yield f"KRC{cmd:02x}", cmd, "8", False
            for cmd in [0x50, 0x52, 0x54, 0x56]:
                yield f"KRL{cmd:02x}", cmd, "12", False
            for cmd in [0x30, 0x32]:
                yield f"OCTMP{cmd:02x}", cmd, "B", False
            for cmd in [0x34, 0x36]:
                yield f"OCTAP{cmd:02x}", cmd, "B", True
        case VideoChipType.TS9347:
            yield "TLM00", 0x00, "24", False
            yield "KRG02", 0x02, "16W", False  # undocumented, same as EF9345
            for cmd in [0x20, 0x22, 0x24, 0x26]:
                yield f"TLA{cmd:02x}", cmd, "24", True
            for cmd in [0x60, 0x62]:
                yield f"TSM{cmd:02x}", cmd, "16", False
            for cmd in [0x70, 0x72, 0x74, 0x76]:
                yield f"TSA{cmd:02x}", cmd, "16", True
            for cmd in [0x40, 0x42, 0x44, 0x46]:
                yield f"KRS{cmd:02x}", cmd, "8", False
            for cmd in [0x50, 0x52, 0x54, 0x56]:
                yield f"KRL{cmd:02x}", cmd, "12", False
            for cmd in [0x30, 0x32]:
                yield f"TBM{cmd:02x}", cmd, "B", False
            for cmd in [0x34, 0x36]:
                yield f"TBA{cmd:02x}", cmd, "B", True


@test(parametric=test_memory_access_generator)
def test_memory_access_write(video: VideoChip, cmd: int, type: str, ap: bool):
    # Set TGS to ensure the chip is in a valid video mode.
    match video.chip_type:
        case VideoChipType.EF9345:
            video.R1 = 0x10
        case VideoChipType.TS9347:
            video.R1 = 0x00
    video.ER0 = 0x81
    video.wait_not_busy()

    # Initially set the whole page to known values.
    video.R1 = 0x55
    video.R2 = 0x55
    video.R3 = 0x55
    video.R6 = 0  # y
    video.R7 = 0  # x
    video.ER0 = 0x05  # CLF/CLL
    time.sleep(0.1)  # leave the command running for a while
    video.ER0 = 0x91  # NOP to stop it.
    video.wait_not_busy()

    # Point the MP to location (0, 0) and the AP to location (1, 0).
    video.R6 = 0  # y (MP)
    video.R7 = 0  # x (MP)
    video.R4 = 0  # y (AP)
    video.R5 = 1  # x (AP)

    # Set registers R1, R2 and R3 to different and execute the command under
    # test. The command will write these values accordingly.
    video.R1 = 0xCC
    video.R2 = 0xBB
    video.R3 = 0xAA
    video.ER0 = cmd
    video.wait_not_busy()

    # Read back the contents of locations (0, 0) and (0, 1).
    video.R6 = 0  # y
    video.R7 = 0  # x
    video.ER0 = 0x09  # KRF/TLM (read) with auto-increment
    video.wait_not_busy()
    loc_mp = video.R1, video.R2, video.R3
    video.ER0 = 0x09  # KRF/TLM (read) with auto-increment
    video.wait_not_busy()
    loc_ap = video.R1, video.R2, video.R3

    # Select the location under test.
    if ap:
        loc_tested, loc_other = loc_ap, loc_mp
    else:
        loc_tested, loc_other = loc_mp, loc_ap

    match type:
        case "24":
            assert loc_tested[0] == 0xCC
            assert loc_tested[1] == 0xBB
            assert loc_tested[2] == 0xAA
            assert loc_other[0] == 0x55  # unaffected
            assert loc_other[1] == 0x55  # unaffected
            assert loc_other[2] == 0x55  # unaffected
        case "16" | "16W":
            assert loc_tested[0] == 0xCC
            assert loc_tested[1] == 0xBB
            assert loc_tested[2] == 0x55  # unaffected
            assert loc_other[0] == 0x55  # unaffected
            assert loc_other[1] == 0x55  # unaffected
            assert loc_other[2] == 0x55  # unaffected
        case "12":
            assert loc_tested[0] == 0xCC
            assert loc_tested[1] == 0x55  # unaffected
            assert loc_tested[2] == 0xA5
            assert loc_other[0] == 0x55  # unaffected
            assert loc_other[1] == 0x55  # unaffected
            assert loc_other[2] == 0x55  # unaffected
        case "8" | "B":
            assert loc_tested[0] == 0xCC
            assert loc_tested[1] == 0x55  # unaffected
            assert loc_tested[2] == 0x55  # unaffected
            assert loc_other[0] == 0x55  # unaffected
            assert loc_other[1] == 0x55  # unaffected
            assert loc_other[2] == 0x55  # unaffected
        case _:
            raise NotImplementedError


@test(parametric=test_memory_access_generator)
def test_memory_access_read(video: VideoChip, cmd: int, type: str, ap: bool):
    # Set TGS to ensure the chip is in a valid video mode.
    match video.chip_type:
        case VideoChipType.EF9345:
            video.R1 = 0x10
        case VideoChipType.TS9347:
            video.R1 = 0x00
    video.ER0 = 0x81
    video.wait_not_busy()

    # Set bytes at location (0, 0) in the first three blocks to known values and
    # bytes at location (1, 0) to different known values.
    video.R6 = 0  # y
    video.R7 = 0  # x
    video.R0 = 0x01  # KRF/TLM with auto-increment
    video.R1 = 0xCC  # to block 0
    video.R2 = 0xBB  # to block 1
    video.ER3 = 0xAA  # to block 2
    video.wait_not_busy()
    video.R1 = 0xFF  # to block 0
    video.R2 = 0xEE  # to block 1
    video.ER3 = 0xDD  # to block 2
    video.wait_not_busy()

    # Point the MP to location (0, 0) and the AP to location (1, 0).
    video.R6 = 0  # y (MP)
    video.R7 = 0  # x (MP)
    video.R4 = 0  # y (AP)
    video.R5 = 1  # x (AP)

    # Set registers R1, R2 and R3 to different and execute the command under
    # test. The command will reload the registers to the known values set above.
    video.R1 = 0x55
    video.R2 = 0x55
    video.R3 = 0x55
    video.ER0 = cmd | 0x08  # set read flag
    video.wait_not_busy()

    match type:
        case "24" | "16W":
            # Note: "16W" commands will populate the 3rd byte anyway.
            assert video.R1 == (0xFF if ap else 0xCC)
            assert video.R2 == (0xEE if ap else 0xBB)
            assert video.R3 == (0xDD if ap else 0xAA)
        case "16":
            assert video.R1 == (0xFF if ap else 0xCC)
            assert video.R2 == (0xEE if ap else 0xBB)
            assert video.R3 == 0x55  # unaffected
        case "12":
            assert video.R1 == (0xFF if ap else 0xCC)
            assert video.R2 == 0x55  # unaffected
            assert video.R3 == 0xAA
        case "8" | "B":
            assert video.R1 == (0xFF if ap else 0xCC)
            assert video.R2 == 0x55  # unaffected
            assert video.R3 == 0x55  # unaffected
        case _:
            raise NotImplementedError


@test(parametric=test_memory_access_generator)
def test_memory_access_incr(video: VideoChip, cmd: int, type: str, ap: bool):
    # Set TGS to ensure the chip is in a valid video mode.
    match video.chip_type:
        case VideoChipType.EF9345:
            video.R1 = 0x10
        case VideoChipType.TS9347:
            video.R1 = 0x00
    video.ER0 = 0x81
    video.wait_not_busy()

    # Set both the MP and the AP to location (0, 0).
    video.R6 = 0  # y (MP)
    video.R7 = 0  # x (MP)
    video.R4 = 0  # y (AP)
    video.R5 = 0  # x (AP)

    # Unlike other commands, 80-column command interleave blocks 0 and 1.
    expected_x_sequence = []
    for i in range(40):
        expected_x_sequence.append(i)  # block 0
        if type in ("8", "12"):
            expected_x_sequence.append(i | 0x80)  # block 1

    for expected_x in expected_x_sequence:
        if ap:
            assert video.R6 == 0  # y (MP)
            assert video.R7 == 0  # x (MP)
            assert video.R4 == 0  # y (AP)
            assert video.R5 == expected_x  # x (AP)
        else:
            assert video.R6 == 0  # y (MP)
            assert video.R7 == expected_x  # x (MP)
            assert video.R4 == 0  # y (AP)
            assert video.R5 == 0  # x (AP)

        # Run the command.
        video.ER0 = cmd | 0x09  # set read and auto-increment flag
        video.wait_not_busy()

    # After the last incrementation, we are now back at column 0.
    # The "Direct byte access" command, via MP only, also increments Y.
    if ap:
        assert video.R6 == 0  # y (MP)
        assert video.R7 == 0  # x (MP)
        assert video.R4 == 0  # y (AP)
        assert video.R5 == 0  # x (AP)
    else:
        assert video.R6 == (1 if type == "B" else 0)  # y (MP)
        assert video.R7 == 0  # x (MP)
        assert video.R4 == 0  # y (AP)
        assert video.R5 == 0  # x (AP)


if __name__ == "__main__":
    test_main()
