from __future__ import annotations

import argparse
import os
import sys
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVarTuple

from .video_chip import VideoChip

_ALL_TESTS: List[_Test] = []

_Parameters = TypeVarTuple("_Parameters")


class _Test:
    def __init__(
        self,
        name: str,
        function: Callable[[VideoChip, *_Parameters], None],
        parameters: Tuple[*_Parameters] = (),
        restrict: Optional[VideoChip] = None,
    ):
        self.name = name
        self.function = lambda video_chip: function(video_chip, *parameters)
        self.restrict = restrict


# A function decorator for marking tests.
def test(
    *,
    parametric: Optional[Dict[str, Tuple[*_Parameters]]] = None,
    restrict: Optional[VideoChip] = None,
):
    def decorator(function: Callable[[VideoChip, *_Parameters], Any]):
        if parametric is None:
            _ALL_TESTS.append(
                _Test(
                    name=function.__name__,
                    function=function,
                    restrict=restrict,
                )
            )
        else:
            for case_name, parameters in parametric.items():
                _ALL_TESTS.append(
                    _Test(
                        name=f"{function.__name__}/{case_name}",
                        function=function,
                        parameters=parameters,
                        restrict=restrict,
                    )
                )
        return function

    return decorator


def _host_and_port(text: str) -> Tuple[str, int]:
    host, sep, port_str = text.rpartition(":")
    port = int(port_str)
    if port < 1 or port > 65535 or sep != ":":
        raise ValueError
    return host, port


def test_main():
    # Parse command-line arguments.
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--video-chip", metavar="HOST:PORT", required=True, type=_host_and_port
    )
    args = parser.parse_args()

    # Change working directory to the tests folder.
    os.chdir(Path(__file__).parent.parent)

    # Connect to the TCP server offering access to the video chip.
    host, port = args.video_chip
    video_chip = VideoChip(host, port)
    video_chip_type = video_chip.chip_type

    # Execute all the tests.
    success_count = 0
    failed_count = 0
    for test in _ALL_TESTS:
        if test.restrict and test.restrict != video_chip_type:
            continue

        # Send NOP and wait, to put the chip into a known initial state.
        video_chip.ER0 = 0x91
        video_chip.wait_not_busy()

        print("RUN  : %s" % test.name, file=sys.stderr)
        success = True
        try:
            test.function(video_chip)
        except:
            traceback.print_exc(file=sys.stderr)
            success = False
        if success:
            print("OK   : %s" % test.name, file=sys.stderr)
            success_count += 1
        else:
            print("FAIL : %s" % test.name, file=sys.stderr)
            failed_count += 1

    total_count = success_count + failed_count
    print(
        f"{success_count} succeeded, {failed_count} failed, {total_count} total.",
        file=sys.stderr,
    )

    if failed_count != 0:
        exit(1)
