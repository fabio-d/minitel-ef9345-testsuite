import itertools
import random
import time
import PIL.Image
from pathlib import Path
from testlib import *
from typing import List, Tuple


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


def test_clear_page_generator(video: VideoChip):
    match video.chip_type:
        case VideoChipType.EF9345:
            commands16 = [0x07]  # CLG
            commands24 = [0x05]  # CLF
        case VideoChipType.TS9347:
            # On the TS9347, test the two undocumented aliases of CLS too.
            commands16 = [0x07, 0x65, 0x67]
            commands24 = [0x05]  # CLL
    for name, args in CLEAR_PAGE_PARAMETERS.items():
        for cmd in commands16:
            yield f"16/{name}/{cmd:02x}", cmd, False, *args
        for cmd in commands24:
            yield f"24/{name}/{cmd:02x}", cmd, True, *args


@test(parametric=test_clear_page_generator)
def test_clear_page(
    video: VideoChip,
    cmd: int,
    width24: bool,  # are we testing a 16-bit (False) or 24-bit (True) clear?
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
    # given position.
    video.R1 = 1
    video.R2 = 2
    video.R3 = 3  # only meaningful in the 24-bit test
    video.R6 = clear_start_y
    video.R7 = clear_start_x
    video.ER0 = cmd
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
        # Verify the last two blocks too.
        video.ER7 = 0x40  # x=0, block=2
        video.wait_not_busy()
        if width24 and y >= expected_cleared_start_y:
            assert video.R1 == 3  # verify that it was modified
        else:
            assert video.R1 == (2 << 6) | y  # verify it was not affected
        assert video.R2 == (3 << 6) | y  # never affected


def test_memory_move_stop_generator(video: VideoChip):
    yield "MVB/MPtoAPa01", 0xD5, 1, True
    yield "MVB/MPtoAPa00", 0xD4, 1, True  # undocumented alias
    yield "MVB/APtoMPa01", 0xD9, 1, False
    yield "MVB/APtoMPa00", 0xD8, 1, False  # undocumented alias
    yield "MVD/MPtoAPa01", 0xE5, 2, True
    yield "MVD/MPtoAPa00", 0xE4, 2, True  # undocumented alias
    yield "MVD/APtoMPa01", 0xE9, 2, False
    yield "MVD/APtoMPa00", 0xE8, 2, False  # undocumented alias
    yield "MVT/MPtoAPa01", 0xF5, 3, True
    yield "MVT/MPtoAPa00", 0xF4, 3, True  # undocumented alias
    yield "MVT/APtoMPa01", 0xF9, 3, False
    yield "MVT/APtoMPa00", 0xF8, 3, False  # undocumented alias


@test(parametric=test_memory_move_stop_generator)
def test_memory_move_stop(
    video: VideoChip,
    cmd: int,
    num_blocks: int,
    mp_to_ap: bool,
):
    # Set TGS to ensure the chip is in a valid video mode.
    match video.chip_type:
        case VideoChipType.EF9345:
            video.R1 = 0x10
        case VideoChipType.TS9347:
            video.R1 = 0x00
    video.ER0 = 0x81
    video.wait_not_busy()

    # Initially set the whole page to zero.
    video.R1 = 0x00
    video.R2 = 0x00
    video.R3 = 0x00
    video.R6 = 0  # y
    video.R7 = 0  # x
    video.ER0 = 0x05  # CLF/CLL
    time.sleep(0.1)  # leave the command running for a while
    video.ER0 = 0x91  # NOP to stop it.
    video.wait_not_busy()

    # Fill row 8 with consective values (even on the blocks that should not be
    # read by the move operation under test).
    video.R6 = 8  # y
    video.R7 = 0  # x
    video.R0 = 0x01  # KRF/TLM with auto-increment
    for i in range(40):
        video.R1 = (1 << 6) | i
        video.R2 = (2 << 6) | i
        video.ER3 = (3 << 6) | i
        video.wait_not_busy()

    if mp_to_ap:
        # Make MP point to (row 8, column 0) and AP to (row 9, column 1).
        video.R4 = 9  # AP y
        video.R5 = 1  # AP x
        video.R6 = 8  # MP y
        video.R7 = 0  # MP x
        video.ER0 = cmd
        video.wait_not_busy()

        # Verify that the operation stopped after 39 columns.
        assert video.R4 == 9
        assert video.R5 == 0  # wrapped
        assert video.R6 == 8
        assert video.R7 == 39
    else:
        # Same as above, but with roles reversed.
        video.R4 = 8  # AP y
        video.R5 = 0  # AP x
        video.R6 = 9  # MP y
        video.R7 = 1  # MP x
        video.ER0 = cmd
        video.wait_not_busy()

        # Verify that the operation stopped after 39 columns.
        assert video.R4 == 8
        assert video.R5 == 39  # wrapped
        assert video.R6 == 9
        assert video.R7 == 0

    # The working register should have been left with the last transferred
    # value.
    assert video.R1 == (num_blocks << 6) | 38

    # Verify the copied values.
    video.R6 = 9  # y
    video.R0 = 0x08  # KRF/TLM + read
    for x in range(40):
        video.ER7 = x  # x
        video.wait_not_busy()
        values = [video.R1, video.R2, video.R3]
        for b in range(num_blocks):
            if x == 0:
                assert values[b] == 0  # first column should be unaffected
            else:
                assert values[b] == ((b + 1) << 6) | (x - 1)


def test_memory_move_nonstop_generator(video: VideoChip):
    yield "MVBa10", 0xD2, 1
    yield "MVBa11", 0xD3, 1  # undocumented alias
    yield "MVDa10", 0xE2, 2
    yield "MVDa11", 0xE3, 2  # undocumented alias
    yield "MVTa10", 0xF2, 3
    yield "MVTa11", 0xF3, 3  # undocumented alias


@test(parametric=test_memory_move_nonstop_generator)
def test_memory_move_nonstop_mp_to_ap(
    video: VideoChip,
    cmd: int,
    num_blocks: int,
):
    # Set TGS to ensure the chip is in a valid video mode.
    match video.chip_type:
        case VideoChipType.EF9345:
            video.R1 = 0x10
        case VideoChipType.TS9347:
            video.R1 = 0x00
    video.ER0 = 0x81
    video.wait_not_busy()

    # Fill row 0 with zeros.
    video.R0 = 0x00  # KRF/TLM
    video.R1 = 0x00
    video.R2 = 0x00
    video.R3 = 0x00
    video.R6 = 0  # y
    for x in range(40):
        video.ER7 = x
        video.wait_not_busy()

    # Fill each row, starting from row 8 with its row number XOR'd with the
    # column number and the block number.
    video.R0 = 0x01  # KRF/TLM with auto-increment
    for y in range(8, 32):
        video.R6 = y
        video.R7 = 0
        for x in range(40):
            video.R1 = y ^ x ^ 1
            video.R2 = y ^ x ^ 2
            video.ER3 = y ^ x ^ 3
            video.wait_not_busy()

    # Start a non-stop move from MP (8, 0) to AP (0, 0). It will repeatedly
    # overwrite row 0 with a different source row. When interrupted, at some
    # unspecified step, row 0 will contain partial data from a given source row
    # and partial data from the previous source row.
    video.R4 = 0  # AP y
    video.R5 = 0  # AP x
    video.R6 = 8  # MP y
    video.R7 = 0  # MP x
    video.ER0 = cmd | 0b0100  # MP to AP
    time.sleep(0.1)  # leave the command running for a while
    video.ER0 = 0x91  # NOP to stop it.
    video.wait_not_busy()

    # Read the resulting buffer, removing the XOR'd column number and block
    # number. The values are stored flattened in a single list.
    video.R6 = 0  # y
    video.R0 = 0x08  # KRF/TLM + read
    values = []
    for x in range(40):
        video.ER7 = x  # x
        video.wait_not_busy()
        values.append(video.R1 ^ x ^ 1)
        if num_blocks >= 2:
            values.append(video.R2 ^ x ^ 2)
        if num_blocks >= 3:
            values.append(video.R3 ^ x ^ 3)

    # Verify that either we interrupted at a an exact row boundary or we stopped
    # with a partial row [A, A, A, ..., B, B, B] (where A and B are consecutive
    # row numbers).
    groups = tuple(k for k, _ in itertools.groupby(values))
    assert len(groups) in [1, 2]
    if len(groups) != 1:
        assert groups == (8, 31) or (groups[0] == groups[1] + 1)


@test(parametric=test_memory_move_nonstop_generator)
def test_memory_move_nonstop_ap_to_mp(
    video: VideoChip,
    cmd: int,
    num_blocks: int,
):
    # Set TGS to ensure the chip is in a valid video mode.
    match video.chip_type:
        case VideoChipType.EF9345:
            video.R1 = 0x10
        case VideoChipType.TS9347:
            video.R1 = 0x00
    video.ER0 = 0x81
    video.wait_not_busy()

    # Initially set the whole page to zero.
    video.R1 = 0x00
    video.R2 = 0x00
    video.R3 = 0x00
    video.R6 = 0  # y
    video.R7 = 0  # x
    video.ER0 = 0x05  # CLF/CLL
    time.sleep(0.1)  # leave the command running for a while
    video.ER0 = 0x91  # NOP to stop it.
    video.wait_not_busy()

    # Fill row 0 with consective values (even on the blocks that should not be
    # read by the move operation under test).
    video.R6 = 0  # y
    video.R7 = 0  # x
    video.R0 = 0x01  # KRF/TLM with auto-increment
    for i in range(40):
        video.R1 = (1 << 6) | i
        video.R2 = (2 << 6) | i
        video.ER3 = (3 << 6) | i
        video.wait_not_busy()

    # Make MP point to (row 9, column 0) and AP to (row 0, column 1). The copy
    # will eventually wrap and even row 8 will be written.
    video.R4 = 0  # AP y
    video.R5 = 1  # AP x
    video.R6 = 9  # MP y
    video.R7 = 0  # MP x
    video.ER0 = cmd | 0b1000  # AP to MP
    time.sleep(0.1)  # leave the command running for a while
    video.ER0 = 0x91  # NOP to stop it.
    video.wait_not_busy()

    # Validate the contents of row 8.
    video.R6 = 8  # y
    video.R0 = 0x08  # KRF/TLM + read
    for x in range(40):
        video.ER7 = x  # x
        video.wait_not_busy()
        values = [video.R1, video.R2, video.R3]
        for b in range(num_blocks):
            if x != 39:
                assert values[b] == ((b + 1) << 6) | (x + 1)
            else:
                assert values[b] == ((b + 1) << 6) | 0


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
def test_memory_access_incr_x(video: VideoChip, cmd: int, type: str, ap: bool):
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
    x_sequence = []  # (initial, incremented)
    for i in range(64):
        # X only wraps to zero in these cases.
        next_i = (i + 1) if i not in [39, 47, 55, 63] else 0

        if type in ("8", "12"):
            x_sequence.append((i, i | 0x80))  # block 0 -> block 1
            x_sequence.append((i | 0x80, next_i))  # block 1 -> block 0
        else:
            x_sequence.append((i, next_i))

    for init_x, incremented_x in x_sequence:
        if ap:
            video.R5 = init_x  # x (AP)
        else:
            video.R7 = init_x  # x (MP)

        # Run the command.
        video.ER0 = cmd | 0x09  # set read and auto-increment flag
        video.wait_not_busy()

        if ap:
            assert video.R6 == 0  # y (MP)
            assert video.R7 == 0  # x (MP)
            assert video.R4 == 0  # y (AP)
            assert video.R5 == incremented_x  # x (AP)
        else:
            # The "Direct byte access" command, via MP only, also increments Y
            # when X wraps to zero.
            incremented_y = 1 if type == "B" and incremented_x == 0 else 0
            assert video.R6 == incremented_y  # y (MP)
            assert video.R7 == incremented_x  # x (MP)
            assert video.R4 == 0  # y (AP)
            assert video.R5 == 0  # x (AP)

            # Cleanup Y for the next iteration.
            video.R6 = 0  # y (MP)

    # The final part of this test validates the Y incrementation. Therefore, it
    # only applies to "Direct byte access" command via MP (see comment above).
    if type != "B" or ap:
        return

    # Validate that Y is incremented by 1, except in the case of wrapping from
    # 31 to 8.
    for i in range(32):
        video.R6 = i  # y (MP)
        video.ER7 = 39  # x (MP), at the end of the row
        video.wait_not_busy()
        assert video.R6 == (i + 1) if i != 31 else 8


# Test INY and its aliases.
@test(parametric={f"INY{cmd:02x}": (cmd,) for cmd in range(0xB0, 0xB0 + 16)})
def test_memory_access_incr_y(video: VideoChip, cmd: int):
    # Set TGS to ensure the chip is in a valid video mode.
    match video.chip_type:
        case VideoChipType.EF9345:
            video.R1 = 0x10
        case VideoChipType.TS9347:
            video.R1 = 0x00
    video.ER0 = 0x81
    video.wait_not_busy()

    video.R0 = cmd  # INY

    # Validate that INY increments by 1, except in the case of wrapping from 31
    # to 8.
    for i in range(32):
        video.ER6 = i
        video.wait_not_busy()
        assert video.R6 == (i + 1) if i != 31 else 8


# Generate the list of MP and AP values pointing to the beginning of each block.
def generate_block_pointers(
    video: VideoChip,
) -> List[Tuple[int, int, int, int]]:
    pointers = []
    for z in range(video.vram_size_kb):
        b = z & 3
        d = z >> 2
        match video.chip_type:
            case VideoChipType.EF9345:
                # MP
                r6 = ((d & 2) << 6) | ((d & 1) << 5)

                # AP
                r6 |= (d & 2) << 5
                r4 = (d & 1) << 5
            case VideoChipType.TS9347:
                r4 = r6 = d << 5
        r7 = r5 = ((b & 2) << 5) | ((b & 1) << 7)
        pointers.append((r4, r5, r6, r7))
    return pointers


@test()
def test_memory_write_mp_read_ap(video: VideoChip):
    # Set TGS to ensure the chip is in a valid video mode.
    match video.chip_type:
        case VideoChipType.EF9345:
            video.R1 = 0x10
        case VideoChipType.TS9347:
            video.R1 = 0x00
    video.ER0 = 0x81
    video.wait_not_busy()

    # Write a different value into each block.
    for i, (r4, r5, r6, r7) in enumerate(generate_block_pointers(video)):
        video.R4 = r4
        video.R5 = r5
        video.R6 = r6
        video.R7 = r7

        # Write zero via the AP to force a known value.
        video.R0 = 0x34  # OCT/TBA
        video.ER1 = 0x00
        video.wait_not_busy()

        # Write the final value via the MP.
        video.R0 = 0x30  # OCT/TBM
        video.ER1 = i ^ 0x55
        video.wait_not_busy()

    # Verify by reading them back via the AP.
    video.R0 = 0x3C  # OCT/TBA + read
    for i, (r4, r5, r6, _) in enumerate(generate_block_pointers(video)):
        video.R4 = r4
        video.R5 = r5
        video.ER6 = r6
        video.wait_not_busy()
        assert video.R1 == i ^ 0x55


@test()
def test_memory_write_ap_read_mp(video: VideoChip):
    # Set TGS to ensure the chip is in a valid video mode.
    match video.chip_type:
        case VideoChipType.EF9345:
            video.R1 = 0x10
        case VideoChipType.TS9347:
            video.R1 = 0x00
    video.ER0 = 0x81
    video.wait_not_busy()

    # Write a different value into each block.
    for i, (r4, r5, r6, r7) in enumerate(generate_block_pointers(video)):
        video.R4 = r4
        video.R5 = r5
        video.R6 = r6
        video.R7 = r7

        # Write zero via the MP to force a known value.
        video.R0 = 0x30  # OCT/TBM
        video.ER1 = 0x00
        video.wait_not_busy()

        # Write the final value via the AP.
        video.R0 = 0x34  # OCT/TBA
        video.ER1 = i ^ 0x55
        video.wait_not_busy()

    # Verify by reading them back via the MP.
    video.R0 = 0x38  # OCT/TBM + read
    for i, (_, _, r6, r7) in enumerate(generate_block_pointers(video)):
        video.R6 = r6
        video.ER7 = r7
        video.wait_not_busy()
        assert video.R1 == i ^ 0x55


# Tests that the unused pointer bits in EF9345 take no part in the address
# decoding. The TS9347 has no unused bits in pointers.
@test(
    parametric={f"{bit}": (1 << bit,) for bit in [6, 7]},
    restrict=VideoChipType.EF9345,
)
def test_unused_pointer_bits(video: VideoChip, r4_extra_bits: int):
    # Set TGS to ensure the chip is in a valid video mode.
    video.R1 = 0x10
    video.ER0 = 0x81
    video.wait_not_busy()

    # Write a marker at (0, 0) via MP and a different marker at (0, 1) via AP.
    video.R4 = 0  # AP y
    video.R5 = 1  # AP x
    video.R6 = 0  # MP y
    video.R7 = 0  # MP x
    video.R0 = 0x30  # OCT via MP
    video.ER1 = 0x11
    video.R0 = 0x34  # OCT via AP
    video.ER1 = 0x12
    video.wait_not_busy()

    # Clobber the unused bits in R4 and write a different value.
    video.R4 = r4_extra_bits  # AP y
    video.R5 = 1  # AP x
    video.R6 = 0  # MP y
    video.R7 = 0  # MP x
    video.R0 = 0x30  # OCT via MP
    video.ER1 = 0x21
    video.R0 = 0x34  # OCT via AP
    video.ER1 = 0x22
    video.wait_not_busy()

    # Read back (without extra bits) and verify.
    video.R4 = 0
    video.ER0 = 0x38  # OCT + read via MP
    video.wait_not_busy()
    assert video.R1 == 0x21
    video.ER0 = 0x3C  # OCT + read via AP
    video.wait_not_busy()
    assert video.R1 == 0x22


def test_memory_access_wrapping_generator(video: VideoChip):
    for z in range(video.vram_size_kb):
        match video.chip_type:
            case VideoChipType.EF9345:
                yield f"KRF_z{z}", 0x00, True, z
                yield f"KRG_z{z}", 0x02, False, z
            case VideoChipType.TS9347:
                yield f"TLM_z{z}", 0x00, True, z
                yield f"TLA_z{z}", 0x22, True, z
                yield f"TSM_z{z}", 0x60, False, z
                yield f"TSA_z{z}", 0x70, False, z
                yield f"KRG_z{z}", 0x02, False, z  # undocumented


# Tests the behavior of multi-byte memory operations crossing a district
# boundary.
@test(parametric=test_memory_access_wrapping_generator)
def test_memory_access_wrapping(video: VideoChip, cmd: int, long: bool, z: int):
    # Set TGS to ensure the chip is in a valid video mode.
    match video.chip_type:
        case VideoChipType.EF9345:
            video.R1 = 0x10
        case VideoChipType.TS9347:
            video.R1 = 0x00
    video.ER0 = 0x81
    video.wait_not_busy()

    # Write an initial value into each of them using a single-byte command.
    video.R0 = 0x30  # OCT/TBM
    expected_contents = []
    for i, (_, _, r6, r7) in enumerate(generate_block_pointers(video)):
        video.R1 = i
        expected_contents.append(i)
        video.R6 = r6
        video.ER7 = r7
        video.wait_not_busy()

    # Set different values at block z (and onwards) with a multi-byte command.
    video.R4, video.R5, video.R6, video.R7 = generate_block_pointers(video)[z]
    z_plus_offset = lambda idx: (z & ~3) | ((z + idx) % 4)
    expected_contents[z_plus_offset(0)] = video.R1 = 0xA1
    expected_contents[z_plus_offset(1)] = video.R2 = 0xA2
    if long:
        expected_contents[z_plus_offset(2)] = video.R3 = 0xA3
    video.ER0 = cmd
    video.wait_not_busy()

    # Verify each memory locations via single-byte commands.
    video.R0 = 0x38  # OCT/TBM + read
    for i, (_, _, r6, r7) in enumerate(generate_block_pointers(video)):
        video.R6 = r6
        video.ER7 = r7
        video.wait_not_busy()
        assert video.R1 == expected_contents[i]


# This test verifies that, when multi-byte writes end up aliasing each other due
# to unconnected address lines, the last one wins. This can only be tested with
# 1 KiB or 2 KiB of VRAM (with more VRAM the accesses always land on distinct
# locations and aliasing never occurs).
@test()
def test_write_aliasing(video: VideoChip):
    # Set TGS to ensure the chip is in a valid video mode.
    match video.chip_type:
        case VideoChipType.EF9345:
            video.R1 = 0x10
        case VideoChipType.TS9347:
            video.R1 = 0x00
    video.ER0 = 0x81
    video.wait_not_busy()

    # Write a known pattern.
    video.R6 = 0  # y
    video.R7 = 0  # x, block
    video.R1 = 0x11
    video.R2 = 0x22
    video.R3 = 0x33
    video.ER0 = 0x00  # KRF/TLM
    video.wait_not_busy()

    # Read back the result.
    video.ER0 = 0x08  # KRF/TLM + read
    video.wait_not_busy()

    match video.vram_size_kb:
        case 1:
            assert video.R1 == 0x33  # aliased
            assert video.R2 == 0x33  # aliased
            assert video.R3 == 0x33
        case 2:
            assert video.R1 == 0x33  # aliased
            assert video.R2 == 0x22
            assert video.R3 == 0x33
        case _:
            raise SkippedTestException("Device has more than 2 KiB of VRAM")


# Tests that changes to ROR take effect at the beginning of the next rendered
# row.
@test()
def test_screen_swap_origin(video: VideoChip):
    # Load templates.
    templ_a = PIL.Image.open("test_memory_data/test_screen_swap_origin_A.png")
    templ_b = PIL.Image.open("test_memory_data/test_screen_swap_origin_B.png")

    # Set 40 columns short mode.
    match video.chip_type:
        case VideoChipType.EF9345:
            tgs = 0x10
            pat = 0xB7
        case VideoChipType.TS9347:
            tgs = 0x40
            pat = 0x33
    video.R1 = tgs
    video.ER0 = 0x81
    video.wait_not_busy()
    video.R1 = pat
    video.ER0 = 0x83
    video.wait_not_busy()

    # MAT
    video.R1 = 0x08
    video.ER0 = 0x82
    video.wait_not_busy()

    # ROR
    video.R1 = 0x08
    video.ER0 = 0x87
    video.wait_not_busy()

    # DOR
    video.R1 = 0x00
    video.ER0 = 0x84
    video.wait_not_busy()

    # Fill screen at blocks 0-1 with white-on-black "A" characters.
    video.R1 = 0x07
    video.R2 = ord("A")
    video.R6 = 0  # y
    video.R7 = 0  # x
    video.ER0 = 0x07  # CLG/CLS
    time.sleep(0.1)
    video.ER0 = 0x91  # NOP to stop it.
    video.wait_not_busy()

    # Fill screen at blocks 2-3 with black-on-white "B" characters.
    video.R1 = 0x47
    video.R2 = ord("B")
    video.R6 = 0  # y
    video.R7 = 0x40  # x
    video.ER0 = 0x07  # CLG/CLS
    time.sleep(0.1)
    video.ER0 = 0x91  # NOP to stop it.
    video.wait_not_busy()

    # Repeatedly flip between the two pages, taking screenshots at semirandom
    # intervals. Verify that at least one of them contains some rows showing all
    # "A" and the remaining rows showing all "B", proving that ROR is latched at
    # the beginning of each row (rather the beginning of the screen, or no
    # latching at all).
    mixed_screenshot_found = False
    sample_at_indices = random.sample(range(2000), k=25)
    for i, ror in enumerate([0x08, 0x48] * 1000):
        video.R1 = ror
        video.ER0 = 0x87
        video.wait_not_busy()

        if i in sample_at_indices:
            # Grab a screenshot and convert it to black and white.
            screenshot = video.screenshot(skip_delay=True).images[0]

            # Count how many rows match templates A and B.
            templ_a_count = 0
            templ_b_count = 0
            for y in range(2, 2 + 10 * 25, 10):  # every text row
                row = screenshot.crop((2, y, 2 + 40 * 8, y + 10))
                if test_images_equal(row, templ_a):
                    templ_a_count += 1
                elif test_images_equal(row, templ_b):
                    templ_b_count += 1
            assert templ_a_count + templ_b_count == 25  # all rows must match

            if templ_a_count > 0 and templ_b_count > 0:
                mixed_screenshot_found = True
    assert mixed_screenshot_found


@test()
def test_read_exec(video: VideoChip):
    # Set TGS to ensure the chip is in a valid video mode.
    match video.chip_type:
        case VideoChipType.EF9345:
            video.R1 = 0x10
        case VideoChipType.TS9347:
            video.R1 = 0x00
    video.ER0 = 0x81
    video.wait_not_busy()

    # Write 0x11 and 0x22 in adjacent locations.
    video.R0 = 0x31  # OCT/TBM with auto-increment
    video.R6 = 0  # y
    video.R7 = 0  # x
    video.ER1 = 0x11
    video.wait_not_busy()
    video.ER1 = 0x22
    video.wait_not_busy()
    assert video.R7 == 2  # x

    # Prepare to read back the 0x11.
    video.R0 = 0x39  # OCT/TBM (read) with auto-increment
    video.R6 = 0  # y
    video.R7 = 0  # x

    # Perform a series of reads with the execution request bit set (i.e. from
    # video.ERn rather than just video.Rn). Verify that we read the value from
    # *before* the execution started.
    readback_x = video.ER7  # R7=0 -> R1=0x11 R7=1
    assert readback_x == 0
    video.wait_not_busy()
    readback_val = video.ER1  # R1=0x11 R7=1 -> R1=0x22 R7=2
    assert readback_val == 0x11
    video.wait_not_busy()
    readback_val = video.ER1  # R1=0x22 R7=2 -> R7=3
    assert readback_val == 0x22
    video.wait_not_busy()
    assert video.R7 == 3  # x

    # Similarly, the busy bit should read as "not busy" (i.e. the state before
    # the execution). Here we test it with "Clear Page", a command that never
    # completes, to avoid race conditions.
    video.R0 = 0x07  # CLG/CLS
    assert (video.ER0 & 0x80) == 0

    # Stop the clear operation, to leave the chip ready for the next test.
    video.ER0 = 0x91  # NOP
    video.wait_not_busy()


if __name__ == "__main__":
    test_main()
