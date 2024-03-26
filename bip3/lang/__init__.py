"""
Defines the multi-language configuration dataclass.
"""

from dataclasses import dataclass, field

import lang.c as C


@dataclass
class MultiConfig:
    c: C.Config = field(default_factory=C.Config)
    cpp: C.Config = field(default_factory=C.Config)
