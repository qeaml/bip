"""
ExeOrLibComponent
"""

import re
from copy import deepcopy
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Optional

import bip.cli as cli
import bip.lang as lang
import bip.lang.c as C
import bip.plat as plat

from .abc import *


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


C_INCLUDE_REGEX = re.compile(
    r'^(?:\s*/\*.*\*/)?\s*#\s*include\s*(?:(?:<(.*)>)|(?:"(.*)"))\s*$'
)


@dataclass
class Stats:
    total_objects = 0  # total amount of object files used in build
    reused_objects = 0  # amount of object files reused from previous build
    compiled_objects = 0  # amount of object files (re)compiled for this build
    compiled_ok = 0  # amount of object files successfully compiled
    compiled_err = 0  # amount of object files that failed to compile


@dataclass
class ExeLibCfg:
    is_lib: bool
    src_dirs: list[Path]
    paths: Paths
    dyn_libs: list[str]
    static_libs: list[str]
    lang_config: lang.MultiConfig
    lang: Language
    recursive: bool


# Component that compiles and links an executable or a shared library.
class ExeOrLibComponent(Component):
    _is_lib: bool
    _src_dirs: list[Path]
    _paths: Paths
    _dyn_libs: list[str]
    _static_libs: list[str]
    _lang: Language
    _c_config: C.Config
    _cpp_config: C.Config
    _recursive: bool
    _stats: Stats

    def __init__(
        self, name: str, out_name: str, platcond: Optional[plat.ID], cfg: ExeLibCfg
    ):
        super(ExeOrLibComponent, self).__init__(name, out_name, platcond)
        self._is_lib = cfg.is_lib
        self._paths = cfg.paths
        self._dyn_libs = cfg.dyn_libs
        self._static_libs = cfg.static_libs
        self._lang = cfg.lang
        self._c_config = cfg.lang_config.c
        self._cpp_config = cfg.lang_config.cpp
        self._reuse_obj = []
        self._compile_obj = []
        if self._is_lib:
            self._out_file = self._paths.out / self._lib_name()
        else:
            self._out_file = self._paths.out / self._exe_name()
        self._src_dirs = cfg.src_dirs
        self._recursive = cfg.recursive
        self._old_files = []
        self._new_files = []
        self._stats = Stats()

        # initially assume C even if CPP is specified.
        # this will be changed to CPP later if necessary.
        if lang == Language.CPP:
            self._lang = Language.C

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

        src = []
        if "src" in raw:
            raw_src = raw["src"]
            if isinstance(raw_src, list):
                src = [base_paths.src / Path(s) for s in raw_src]
            else:
                src = [base_paths.src / Path(raw_src)]
        else:
            src = [base_paths.src / name]

        real_lang_config = deepcopy(lang_config)
        if "c" in raw:
            real_lang_config.c.load_overrides(raw.pop("c"))
        if "cpp" in raw:
            real_lang_config.cpp.load_overrides(raw.pop("cpp"))

        dyn_libs = []
        if "libs" in raw:
            cli.warn(f"`libs` key is deprecated.",
                "Use `dyn-libs` or `static-libs` instead.")
            dyn_libs.extend(raw.pop("libs"))
        if "dyn-libs" in raw:
            dyn_libs.extend(raw.pop("dyn-libs"))

        static_libs = []
        # if "static-libs" in raw:
        #     static_libs.extend(raw.pop("static-libs"))

        recursive = True
        if "recursive" in raw:
            recursive = raw.pop("recursive")

        cfg = ExeLibCfg(
            is_lib,
            src,
            base_paths,
            dyn_libs,
            static_libs,
            real_lang_config,
            lang,
            recursive,
        )

        return cls(name, out_name, platform, cfg)

    _old_files: set[Path]
    _new_files: set[Path]

    def _is_old_file(self, file: Path, out: Path) -> bool:
        # print("file", file, end="")
        if not file.exists():
            # print(" does not exist")
            return False
        if not out.exists():
            # print(" is new (output doesn't exist)")
            self._new_files.append(file)
            return False
        if file in self._old_files:
            # print(" is old (from cache)")
            return True
        if file in self._new_files:
            # print(" is new (from cache)")
            return False
        out_mtime = out.stat().st_mtime
        file_mtime = file.stat().st_mtime
        if file_mtime > out_mtime:
            # print(" is new")
            self._new_files.append(file)
            return False
        # print(" is old")
        self._old_files.append(file)
        return True

    _reuse_obj: list[CodeObject]
    _compile_obj: list[CodeObject]
    _out_file: Path

    def _add_obj(self, root: Path, src: Path) -> None:
        obj_ext = plat.OBJ_EXT[plat.native()]

        ext = src.suffix.lower()
        src_lang = self._lang
        if self._lang == Language.C:
            if ext in CPP_EXTS:
                self._lang = Language.CPP
                src_lang = Language.CPP
                # print("(swapping to cpp)")
            elif ext not in C_EXTS:
                return
        elif self._lang == Language.CPP:
            if ext in C_EXTS:
                src_lang = Language.C
            elif ext not in CPP_EXTS:
                return
        elif self._lang == Language.GO:
            if ext not in GO_EXTS:
                return

        obj = self._paths.obj / src.relative_to(root).with_suffix(obj_ext)
        # print(src, "(", src_lang, ") ->", obj)
        self._stats.total_objects += 1
        if self._is_old_file(src, obj):
            self._stats.reused_objects += 1
            self._reuse_obj.append(CodeObject(src_lang, src, obj))
            return

        self._compile_obj.append(CodeObject(src_lang, src, obj))
        self._stats.compiled_objects += 1

    def _discover_obj(self, root: Path, sub: Path, recurse: bool) -> None:
        if not sub.exists():
            cli.warn(f"source {sub} does not exist")
            return
        if sub.is_file():
            self._add_obj(root, sub)
            return
        if not sub.is_dir():
            return
        for src in sub.iterdir():
            if recurse:
                self._discover_obj(root, src, True)
            elif src.is_file():
                self._add_obj(root, src)

    def want_run(self) -> bool:
        for root in self._src_dirs:
            self._discover_obj(self._paths.src, root, self._recursive)
        return len(self._compile_obj) > 0 or not self._out_file.exists()

    def _exe_name(self) -> str:
        match plat.native():
            case plat.ID.WINDOWS:
                return self.out_name + ".exe"
            case _:
                return self.out_name

    def _lib_name(self) -> str:
        match plat.native():
            case plat.ID.WINDOWS:
                return self.out_name + ".dll"
            case _:
                return "lib" + self.out_name + ".so"

    def _build_c(self, info: RunInfo) -> bool:
        cli.progress(f"{self.name}")

        parent = self._out_file.parent
        if not parent.exists():
            parent.mkdir(parents=True)

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

        link_exe: str
        if self._lang == Language.C:
            if compiler.c_compiler is None:
                cli.error(f"Chosen compiler ({compiler.name}) does not support C")
                return False
            link_exe = compiler.c_compiler
        if self._lang == Language.CPP:
            if compiler.cpp_compiler is None:
                cli.error(f"Chosen compiler ({compiler.name}) does not support C++")
                return False
            link_exe = compiler.cpp_compiler

        c_std = (
            self._c_config.std if self._c_config.std is not None else C.DEFAULT_C_STD
        )
        cpp_std = (
            self._cpp_config.std
            if self._cpp_config.std is not None
            else C.DEFAULT_CPP_STD
        )

        obj_fail = False
        for obj in self._compile_obj:
            cfg = self._c_config
            std = c_std
            obj_exe = compiler.c_compiler
            if obj.lang == Language.CPP:
                cfg = self._cpp_config
                std = cpp_std
                obj_exe = compiler.cpp_compiler

            if not obj.obj.parent.exists():
                obj.obj.parent.mkdir(parents=True)

            info = C.ObjectInfo(
                cfg,
                obj.src,
                obj.obj,
                cfg.include,
                info.release,
                cfg.define,
                obj.lang == Language.CPP,
                std,
                self._is_lib,
            )
            cli.progress(f"  {obj.obj.name}")
            out = cli.cmd_out(obj_exe, C.obj_args(compiler.style, info))
            if not out.success:
                self._stats.compiled_err += 1
                obj_fail = True
            else:
                self._stats.compiled_ok += 1

            if len(out.stdout) > 0:
                cli.wrapped(3, out.stdout.decode("utf-8").strip())
            if len(out.stderr) > 0:
                cli.wrapped(3, out.stderr.decode("utf-8").strip())

        if obj_fail:
            cli.failure(
                f" Fail. {self._stats.compiled_ok}/{self._stats.compiled_objects} objects compiled"
            )
            return False

        info = C.LinkInfo(
            cmpnt_cfg,
            [obj.obj for obj in self._compile_obj + self._reuse_obj],
            self._out_file,
            [self._paths.out],
            self._dyn_libs,
            self._static_libs,
            info.release,
            self._lang == Language.CPP,
            None,
        )
        cli.progress(f"  {self._out_file.name}")
        if self._is_lib:
            success = cli.cmd(link_exe, C.lib_args(compiler.style, info))
        else:
            success = cli.cmd(link_exe, C.exe_args(compiler.style, info))

        if success:
            cli.success(
                f" OK. {self._stats.compiled_ok} objects compiled, {self._stats.reused_objects} objects reused"
            )
        else:
            cli.failure(f" Fail. Could not link.")
        return success

    def run(self, info: RunInfo) -> bool:
        if self._lang == Language.C or self._lang == Language.CPP:
            return self._build_c(info)
        if self._lang == Language.GO:
            return self._build_go(info)
        return False

    def clean(self) -> bool:
        for root in self._src_dirs:
            self._discover_obj(self._paths.src, root, self._recursive)
        for obj in self._compile_obj + self._reuse_obj:
            if obj.obj.exists():
                obj.obj.unlink()
        return False

    def contrib(self) -> list[Contrib]:
        if self._is_lib:
            return [Contrib.lib(self.name, self._out_file)]
        return [Contrib.exe(self.name, self._out_file)]
