import re
from dataclasses import dataclass
from enum import IntEnum
from typing import Optional

VERSION = (3, 2)
VERSION_NUM = (VERSION[0] << 16) | VERSION[1]
VERSION_STR = f"{VERSION[0]}.{VERSION[1]}"


REQR_REGEX = re.compile("^(<|<=|=|==|>=|>)?(\\d+)\\.(\\d+)(\\+)?$")


class Comparator(IntEnum):
    LOWER = -2
    LOWER_EQUAL = -1
    EQUAL = 0
    GREATER_EQUAL = 1
    GREATER = 2


@dataclass
class Reqr:
    comparator: Comparator
    major: int
    minor: int

    def is_satisfied(self) -> bool:
        match self.comparator:
            case Comparator.LOWER:
                if VERSION[0] >= self.major:
                    return False
                if VERSION[1] >= self.minor:
                    return False
                return True
            case Comparator.LOWER_EQUAL:
                if VERSION[0] > self.major:
                    return False
                if VERSION[1] > self.minor:
                    return False
                return True
            case Comparator.EQUAL:
                if VERSION[0] != self.major:
                    return False
                if VERSION[1] != self.minor:
                    return False
                return True
            case Comparator.GREATER_EQUAL:
                if VERSION[0] < self.major:
                    return False
                if VERSION[1] < self.minor:
                    return False
                return True
            case Comparator.GREATER:
                if VERSION[0] <= self.major:
                    return False
                if VERSION[1] <= self.minor:
                    return False
                return True


def parse_reqr(raw: str) -> Optional[Reqr]:
    res = REQR_REGEX.fullmatch(raw)
    if res is None:
        return None

    comparator = None
    comp_pre = res.group(1)
    if comp_pre is not None:
        match comp_pre:
            case "<":
                comparator = Comparator.LOWER
            case "<=":
                comparator = Comparator.LOWER_EQUAL
            case "=", "==":
                comparator = Comparator.EQUAL
            case ">=":
                comparator = Comparator.GREATER_EQUAL
            case ">":
                comparator = Comparator.GREATER

    comp_suffix = res.group(4)
    if comp_suffix is not None:
        if comparator is not None:
            return None
        comparator = Comparator.GREATER_EQUAL

    if comparator is None:
        comparator = Comparator.EQUAL

    major = int(res.group(2))
    minor = int(res.group(3))
    return Reqr(comparator, major, minor)
