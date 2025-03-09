import argparse
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Set

DESCRIPTION = "Applies formatting rules to source files in this repository."
EPILOG = """
If no files are explicitly listed, all files known to git will be formatted.
"""


# Returns all the files that are currently registered with git.
def git_ls_files() -> Set[Path]:
    with subprocess.Popen(
        ["git", "ls-files"],
        stdout=subprocess.PIPE,
        universal_newlines=True,
    ) as proc:
        lines = proc.stdout.readlines()
        if proc.wait() != 0:
            raise RuntimeError("git ls-files failed: %d", proc.returncode)
    return {Path(line.strip()) for line in lines}


# Runs the given command, optionally printing the command line and, if the
# executable cannot be found, a hint on how to install it.
def run_command(
    cmdline: List[str],
    verbose: bool,
    *,
    install_hint: Optional[str] = None,
):
    if verbose:
        print("+", *map(shlex.quote, cmdline), file=sys.stderr)
    try:
        subprocess.check_call(cmdline)
    except FileNotFoundError:
        print(f"Warning! {cmdline[0]} is not installed.", file=sys.stderr)
        if install_hint:
            print(f"Hint: Install with {install_hint}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description=DESCRIPTION,
        epilog=EPILOG.strip(),
    )
    parser.add_argument("file", nargs="*", help="Format specific file(s)")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    selected_files = sorted(Path(path).absolute() for path in args.file)

    os.chdir(Path(__file__).parent.parent)
    if args.verbose:
        print("+", "cd", shlex.quote(os.getcwd()), file=sys.stderr)

    # Was the list of files to be formatted given via command line?
    if selected_files:
        explicit_selection = True
    else:
        selected_files = sorted(git_ls_files())
        explicit_selection = False

    c_files = list()
    lua_files = list()
    python_files = list()
    for path in sorted(selected_files):
        if not path.is_file():
            # The file does not exist: show a warning, but only if it was
            # explicitly listed in the command line.
            if explicit_selection:
                print(f"Warning! {path}: cannot find file", file=sys.stderr)
        elif path.suffix == ".c":
            c_files.append(str(path))
        elif path.suffix == ".lua":
            lua_files.append(str(path))
        elif path.suffix == ".py":
            python_files.append(str(path))
        else:
            # We don't know how to format the file: show a warning, but only if
            # it was explicitly listed in the command line.
            if explicit_selection:
                print(f"Warning! {path}: no formatting rule", file=sys.stderr)

    if c_files:
        run_command(
            ["clang-format", "-i", *c_files],
            args.verbose,
            install_hint="sudo apt install clang-format",
        )
    if lua_files:
        run_command(
            ["lua-format", "-i", *lua_files],
            args.verbose,
            install_hint="https://github.com/Koihik/LuaFormatter/blob/master/README.md#install",
        )
    if python_files:
        run_command(
            ["black", "--quiet", *python_files],
            args.verbose,
            install_hint="sudo apt install black",
        )
        run_command(
            ["isort", "--quiet", *python_files],
            args.verbose,
            install_hint="sudo apt install isort",
        )


if __name__ == "__main__":
    main()
