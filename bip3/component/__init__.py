"""
Component definitions.
"""


from enum import StrEnum
from typing import Optional

import cli
import lang
import plat

from .abc import Component, Paths
from .exelib import ExeOrLibComponent
from .plug import PlugComponent


# Represents the kind of component. This is used to read the rest of a
# component's information from the recipe file.
class Kind(StrEnum):
    EXE = "exe"
    LIB = "lib"
    PLUG = "plug"


# Create a component from a dictionary.
def from_dict(
    raw: dict, name: str, base_paths: Paths, lang_config: lang.MultiConfig
) -> Optional[Component]:
    platcond = None
    if "platform" in raw:
        platname = raw["platform"]
        platcond = plat.find(platname)
        if platcond is None:
            supported_plats = ", ".join(plat.NAMES.keys())
            cli.error(
                f"Unknown platform '{platname}'.",
                f"Supported platforms: {supported_plats}",
            )
            return None

    kind = None
    out_name = None
    for k in Kind:
        if k.value in raw:
            kind = k
            out_name = raw.pop(k.value)
            break

    if kind is None:
        supported_kinds = ",".join(k.value for k in Kind)
        cli.error(
            f"Could not determine kind of component '{name}'.",
            f"Supported kinds of components: {supported_kinds}",
        )
        return None

    match kind:
        case Kind.EXE:
            return ExeOrLibComponent.from_dict(
                raw, name, out_name, platcond, False, base_paths, lang_config
            )
        case Kind.LIB:
            return ExeOrLibComponent.from_dict(
                raw, name, out_name, platcond, True, base_paths, lang_config
            )
        case Kind.PLUG:
            return PlugComponent.from_dict(raw, name, out_name, platcond, base_paths)

    cli.error(f"Component kind '{kind.value}' currently unimplemented.")
    return None
