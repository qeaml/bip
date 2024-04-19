"""
Platform detection.
"""

from enum import IntEnum, auto
from platform import system
from typing import Optional


# A simple identifier for the supported platforms.
class ID(IntEnum):
    # Generic Linux
    LINUX = auto()
    # Windows
    WINDOWS = auto()
    # Mac
    DARWIN = auto()


# Various names that can be used to refer to the various platforms.
NAMES = {
    "linux": ID.LINUX,
    "windows": ID.WINDOWS,
    "win": ID.WINDOWS,
    "win32": ID.WINDOWS,
    "darwin": ID.DARWIN,
    "macosx": ID.DARWIN,
    "macos": ID.DARWIN,
    "mac": ID.DARWIN,
}


# Extensions used for object files
OBJ_EXT = {
    ID.LINUX: ".o",
    ID.WINDOWS: ".obj",
    ID.DARWIN: ".o",
}


# Try to find a platform ID given its name, return None otherwise.
def find(name: str) -> Optional[ID]:
    if name.lower() in NAMES:
        return NAMES[name.lower()]
    return None


# Determine what platform we are running on. If we cannot reliably determine, we
# just assume LINUX is close enough.
def native() -> ID:
    match system():
        case "Linux":
            return ID.LINUX
        case "Windows":
            return ID.WINDOWS
        case "Darwin":
            return ID.DARWIN
        case _:
            return ID.LINUX
