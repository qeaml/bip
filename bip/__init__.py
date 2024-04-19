"""
Main import file for bip's API.
"""

from pathlib import Path

import bip.plat as plat

from .cli import error, note, progress, warn, cmd
from .version import VERSION

__all__ = ["note", "warn", "error", "progress", "cmd", "plat", "Path", "VERSION"]
