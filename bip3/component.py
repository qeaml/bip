"""
Component definitions.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Optional

import cli
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


# Represents the kind of component. This is used to read the rest of a
# component's information from the recipe file.
class Kind(StrEnum):
    EXE = "exe"
    LIB = "lib"
    PLUG = "plug"


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


# Language is used by EXE and LIB components.
class Language(StrEnum):
    C = "c"
    CPP = "cpp"
    GO = "go"


C_EXTS = (".c")
CPP_EXTS = (".cpp", ".cxx", ".cc")
GO_EXTS = (".go")


@dataclass
class CodeObject:
    # used to discern C and C++ specifically
    lang: Language
    src: Path
    obj: Path

# Component that compiles and links an executable or a shared library.
class ExeOrLibComponent(Component):
    _is_lib: bool
    _paths: Paths
    _lang: Language

    def __init__(
        self,
        name: str,
        platcond: Optional[plat.ID],
        is_lib: bool,
        paths: Paths,
        lang: Language,
    ):
        super(ExeOrLibComponent, self).__init__(name, platcond)
        self._is_lib = is_lib
        self._paths = paths
        self._lang = lang
        self._reuse_obj = []
        self._compile_obj = []

        # initially assume C even if CPP is specified.
        # this will be changed to CPP later if necessary.
        if lang == Language.CPP:
            self._lang = Language.C

    @classmethod
    def from_dict(
        cls,
        raw: dict,
        name: str,
        platform: Optional[plat.ID],
        is_lib: bool,
        base_paths: Paths,
    ) -> Optional[Component]:
        if "lang" not in raw:
            cli.error(
                "Executable and library components must specify a language.",
                "Specify it using the 'lang' key.",
            )
            return None
        langname = raw["lang"].upper()
        lang: Language
        try:
            lang = Language[langname]
        except KeyError:
            supported_langs = ", ".join(l.name for l in Language)
            cli.error(
                f"Unknown language {langname}.",
                f"Supported languages: {supported_langs}",
            )
            return None

        src: Path
        if "src" in raw:
            src = base_paths.src / Path(raw["src"])
        else:
            src = base_paths.src / name

        obj: Path
        if "obj" in raw:
            obj = base_paths.obj / Path(raw["obj"])
        else:
            obj = base_paths.obj / name

        out: Path
        if "out" in raw:
            out = base_paths.out / Path(raw["out"])
        else:
            out = base_paths.out

        return cls(name, platform, is_lib, Paths(src, obj, out), lang)

    _reuse_obj: list[CodeObject]
    _compile_obj: list[CodeObject]

    def _add_obj(self, lang: Language, src: Path, obj: Path):
        if obj.exists():
            if obj.stat().st_mtime >= src.stat().st_mtime:
                self._reuse_obj.append(CodeObject(lang, src, obj))
                print("reuse", obj)
                return
        self._compile_obj.append(CodeObject(lang, src, obj))
        print("compile", obj)
        if not obj.parent.exists():
            print("creating", obj.parent)
            obj.parent.mkdir(parents=True)

    def _discover_obj(self, root: Path) -> None:
        obj_ext = plat.OBJ_EXT[plat.native()]
        for src in root.iterdir():
            if src.is_dir():
                _discover_obj(src)
                continue
            if not src.is_file():
                continue

            ext = src.suffix.lower()
            src_lang = self._lang
            if self._lang == Language.C:
                if ext in CPP_EXTS:
                    self._lang = Language.CPP
                    src_lang = Language.CPP
                    print("(swapping to cpp)")
                elif ext not in C_EXTS:
                    continue
            elif self._lang == Language.CPP:
                if ext in C_EXTS:
                    src_lang = Language.C
                elif ext not in CPP_EXTS:
                    continue
            elif self._lang == Language.GO:
                if ext not in GO_EXTS:
                    continue

            obj = self._paths.obj / src.relative_to(root).with_suffix(obj_ext)
            print(src, "(", src_lang, ") ->", obj)
            self._add_obj(src_lang, src, obj)

    def want_run(self) -> bool:
        self._discover_obj(self._paths.src)
        return len(self._compile_obj) > 0

    def run(self) -> bool:
        # TODO
        return False

    def clean(self) -> bool:
        self._discover_obj(self._paths.src)
        # TODO
        return False


# Create a component from a dictionary.
def from_dict(raw: dict, name: str, base_paths: Paths) -> Optional[Component]:
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
    for k in Kind:
        if k.value in raw:
            kind = k
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
            return ExeOrLibComponent.from_dict(raw, name, platcond, False, base_paths)
        case Kind.LIB:
            return ExeOrLibComponent.from_dict(raw, name, platcond, True, base_paths)

    cli.error(f"Component kind '{kind.value}' currently unimplemented.")
    return None
