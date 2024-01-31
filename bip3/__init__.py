"""
Main import file for bip's API.
"""

import bip3.plat

from .cli import error, note, progress, warn

__all__ = ["note", "warn", "error", "progress", "plat"]
