"""
Component abstract base class.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import plat


# Paths commonly used across different kinds of components.
@dataclass
class Paths:
    src: Path
    obj: Path
    out: Path

    @classmethod
    def from_dict(cls, raw: dict) -> "Paths":
        src: Path
        if "src" in raw:
            src = Path(raw["src"])
        else:
            src = Path(".")

        out: Path
        if "out" in raw:
            out = Path(raw["out"])
        else:
            out = Path(".")

        obj: Path
        if "obj" in raw:
            obj = Path(raw["obj"])
        else:
            obj = Path(".")

        return cls(src, obj, out)


# A component is the smallest unit of a recipe file.
class Component(ABC):
    # Unique name of this component.
    name: str
    # Platform restriction for this component.
    platform: Optional[plat.ID]

    @abstractmethod
    def __init__(self, name: str, platcond: Optional[plat.ID]):
        self.name = name
        self.platform = platcond

    # Check whether this component wants to run. This is also useful for preparing
    # a later run.
    @abstractmethod
    def want_run(self) -> bool:
        return True

    # Execute this component. Whether that'd be compiling some code or running
    # plugin code.
    @abstractmethod
    def run(self) -> bool:
        pass

    # Remove all run artifacts.
    @abstractmethod
    def clean(self) -> bool:
        return True
