"""
ExeOrLibComponent
"""

from copy import deepcopy
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Optional

import cli
import lang
import lang.c as C
import plat

from .abc import Component, Paths, RunInfo


# Language is used by EXE and LIB components.
class Language(StrEnum):
    C = "c"
    CPP = "cpp"
    GO = "go"


C_EXTS = (".c",)
CPP_EXTS = (".cpp", ".cxx", ".cc")
GO_EXTS = (".go",)


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
    _libs: list[str]
    _lang: Language
    _c_config: C.Config
    _cpp_config: C.Config

    def __init__(
        self,
        name: str,
        out_name: str,
        platcond: Optional[plat.ID],
        is_lib: bool,
        paths: Paths,
        libs: list[str],
        lang_config: lang.MultiConfig,
        lang: Language,
    ):
        super(ExeOrLibComponent, self).__init__(name, out_name, platcond)
        self._is_lib = is_lib
        self._paths = paths
        self._libs = libs
        self._lang = lang
        self._c_config = lang_config.c
        self._cpp_config = lang_config.cpp
        self._reuse_obj = []
        self._compile_obj = []
        if is_lib:
            self._out_file = self._paths.out / self._lib_name()
        else:
            self._out_file = self._paths.out / self._exe_name()

        # initially assume C even if CPP is specified.
        # this will be changed to CPP later if necessary.
        if lang == Language.CPP:
            self._lang = Language.C

        print(" ", name, "C config:", self._c_config)
        print(" ", name, "C++ config:", self._cpp_config)

    @classmethod
    def from_dict(
        cls,
        raw: dict,
        name: str,
        out_name: str,
        platform: Optional[plat.ID],
        is_lib: bool,
        base_paths: Paths,
        lang_config: lang.MultiConfig,
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

        real_lang_config = deepcopy(lang_config)
        if "c" in raw:
            real_lang_config.c.load_overrides(raw.pop("c"))
        if "cpp" in raw:
            real_lang_config.cpp.load_overrides(raw.pop("cpp"))

        libs = []
        if "libs" in raw:
            libs = raw.pop("libs")

        return cls(
            name,
            out_name,
            platform,
            is_lib,
            Paths(src, obj, out),
            libs,
            real_lang_config,
            lang,
        )

    _reuse_obj: list[CodeObject]
    _compile_obj: list[CodeObject]
    _out_file: Path

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

    def _discover_obj(self, root: Path, sub: Path) -> None:
        obj_ext = plat.OBJ_EXT[plat.native()]
        for src in sub.iterdir():
            if src.is_dir():
                self._discover_obj(root, src)
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
        self._discover_obj(self._paths.src, self._paths.src)
        return len(self._compile_obj) > 0 or not self._out_file.exists()

    def _exe_name(self) -> str:
        match plat.native():
            case plat.ID.WINDOWS:
                return self.out_name + ".EXE"
            case _:
                return self.out_name

    def _lib_name(self) -> str:
        match plat.native():
            case plat.ID.WINDOWS:
                return self.out_name + ".DLL"
            case _:
                return "lib" + self.out_name + ".so"

    def _build_c(self, info: RunInfo) -> bool:
        cmpnt_cfg = self._c_config
        if self._lang == Language.CPP:
            cmpnt_cfg = self._cpp_config

        compiler: Optional[C.Compiler]
        if cmpnt_cfg.compiler is not None:
            compiler = C.has_compiler(cmpnt_cfg.compiler)
            if compiler is None:
                cli.error(
                    f"Specified compiler ({cmpnt_cfg.compiler}) is not present in current environment"
                )
                return False
        else:
            compiler = C.default_compiler()
            if compiler is None:
                cli.error("Could not find viable C/C++ compiler")
                return False

        exe: str
        if self._lang == Language.C:
            if compiler.c_compiler is None:
                cli.error(f"Chosen compiler ({compiler.name}) does not support C")
                return False
            exe = compiler.c_compiler
        if self._lang == Language.CPP:
            if compiler.cpp_compiler is None:
                cli.error(f"Chosen compiler ({compiler.name}) does not support C++")
                return False
            exe = compiler.cpp_compiler

        c_std = (
            self._c_config.std if self._c_config.std is not None else C.DEFAULT_C_STD
        )
        cpp_std = (
            self._cpp_config.std
            if self._cpp_config.std is not None
            else C.DEFAULT_CPP_STD
        )

        for obj in self._compile_obj:
            cfg = self._c_config
            std = c_std
            if obj.lang == Language.CPP:
                cfg = self._cpp_config
                std = cpp_std

            info = C.ObjectInfo(
                obj.src,
                obj.obj,
                cfg.include,
                info.optimized,
                cfg.define,
                obj.lang == Language.CPP,
                std,
                self._is_lib,
            )
            cli.cmd(exe, C.obj_args(compiler.style, info))

        info = C.LinkInfo(
            [obj.obj for obj in self._compile_obj + self._reuse_obj],
            self._out_file,
            [self._paths.out],
            self._libs,
            info.optimized,
            self._lang == Language.CPP,
            None,
        )
        if self._is_lib:
            cli.cmd(exe, C.lib_args(compiler.style, info))
        else:
            cli.cmd(exe, C.exe_args(compiler.style, info))
        return True

    def run(self, info: RunInfo) -> bool:
        if self._lang == Language.C or self._lang == Language.CPP:
            return self._build_c(info)
        if self._lang == Language.GO:
            return self._build_go(info)
        return False

    def clean(self) -> bool:
        self._discover_obj(self._paths.src, self._paths.src)
        # TODO
        return False
