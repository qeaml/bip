"""
Command-line argument parsing & terminal output.
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Args:
    # Name of the invoked program.
    program: str
    # Positional arguments.
    pos: list[str]
    # Flags: `/abc`, `-abc`, `--abc`
    flags: list[str]
    # Named arguments: `/name:value`, `/name=value`, `--name:value`, `--name=value`
    named: dict[str, str]


def _find_either(s: str, a: str, b: str) -> int:
    if idx := s.find(a):
        return idx
    return s.find(b)


def parse(args: list[str]) -> Args:
    program = args[0]
    pos: list[str] = []
    flags: list[str] = []
    named: dict[str, str] = {}
    if len(args) < 2:
        return Args(program, pos, flags, named)
    for a in args[1:]:
        if a.startswith("--"):
            val_idx = _find_either(a, "=", ":")
            if val_idx == -1:
                flags.append(a[2:].lower())
            else:
                named[a[2:val_idx].lower()] = a[val_idx + 1 :].lower()
        # elif a.startswith("/"):
        #     val_idx = _find_either(a, "=", ":")
        #     if val_idx == -1:
        #         flags.append(a[1:])
        #     else:
        #         named[a[1:val_idx]] = a[val_idx + 1 :]
        elif a.startswith("-"):
            flags.append(a[1:].lower())
        else:
            pos.append(a.lower())
    return Args(program, pos, flags, named)


BOLD = "\x1b[1m"
NO_BOLD = "\x1b[22m"

RED = "\x1b[31m"
YELLOW = "\x1b[33m"
CYAN = "\x1b[36m"
DEFAULT = "\x1b[39m"


def message(title: str, color: str, text: str, tip: Optional[str] = None) -> None:
    print()
    print(f" {color}{title} |{DEFAULT} {BOLD}{text}{NO_BOLD}")
    if tip:
        print(f"       {color}|{DEFAULT} Tip: {tip}")


def note(text: str, tip: Optional[str] = None) -> None:
    message(" note", CYAN, text, tip)


def warn(text: str, tip: Optional[str] = None) -> None:
    message(" warn", YELLOW, text, tip)


def error(text: str, tip: Optional[str] = None) -> None:
    message("error", RED, text, tip)


def progress(text: str) -> None:
    print(f"{BOLD}{text}{NO_BOLD}")


# Quote an argument if necessary
def quote(arg: str) -> str:
    if " " in arg or "\t" in arg:
        return f'"{arg}"'
    return arg


# Join arguments into a string.
def join(args: list[str]) -> str:
    return " ".join(quote(a) for a in args)


# Run a command
def cmd(exe: str, args: list[str]) -> bool:
    full = join([exe, *args])
    progress(f"$ {full}")
    return subprocess.run(full, shell=True).returncode == 0
