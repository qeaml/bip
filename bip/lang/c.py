"""
C and C++ language support.
"""

import struct
from dataclasses import dataclass, field
from enum import IntEnum, auto
from pathlib import Path
from shutil import which
from typing import Any, Optional

import bip.cli as cli
import bip.plat as plat
from bip.version import VERSION_NUM


# CLI argument style for compiler invocations. This also decides the object file
# extension.
class FlagStyle(IntEnum):
    # similar to GCC,G++
    GNU = auto()
    # similar to CL.EXE
    MSC = auto()


DEFAULT_C_STD = "c17"
DEFAULT_CPP_STD = "c++20"


@dataclass
class Config:
    # Which compiler should be used. If not specified, then a default one is
    # determined based on the current platform.
    compiler: Optional[str] = None
    # Which C/C++ standard to use. If not specified, then a default of C17 and
    # C++20 is used.
    std: Optional[str] = None
    # Additional include directories.
    include: list[Path] = field(default_factory=list)
    # Preprocessor definitions. If a value is not specified, then the compiler
    # defines the default, usually 1.
    define: dict[str, Optional[str]] = field(default_factory=dict)
    # C++: Disable exceptions.
    noexcept: bool = False
    # Should symbols default to hidden visibility (for GNU-like compilers on
    # non-Windows platforms)
    hide_symbols: bool = False

    # Load overrides from a dictionary
    def load_overrides(self, raw: dict[str, Any]):
        if "compiler" in raw:
            self.compiler = raw.pop("compiler")
        if "std" in raw:
            self.std = raw.pop("std")
        if "define" in raw:
            self.define.update(raw.pop("define"))
        if "include" in raw:
            self.include.extend(raw.pop("include"))
        if "noexcept" in raw:
            self.noexcept = raw.pop("noexcept")
        if "hide_symbols" in raw:
            self.hide_symbols = raw.pop("hide_symbols")
        if "hide-symbols" in raw:
            self.hide_symbols = raw.pop("hide-symbols")


# Information to compile an object file.
@dataclass
class ObjectInfo:
    cfg: Config
    # Source file.
    src: Path
    # Output object file.
    out: Path
    # Include directories.
    include: list[Path]
    # Build with optimizations?
    release: bool
    # Extra preprocessor defines.
    defines: dict[str, Optional[str]]
    # Is this a C++ file?
    is_cpp: bool
    # Which C/C++ standard to use.
    std: str
    pic: bool


MSC_VERSION_DEF = f"/D_BIP={VERSION_NUM}"
GNU_VERSION_DEF = f"-D_BIP={VERSION_NUM}"


def _gnu_obj_args(info: ObjectInfo) -> list[str]:
    flags = []

    flags.extend(["-c", str(info.src), "-o", str(info.out)])

    for i in info.include:
        flags.append(f"-I{i}")

    if plat.native() != plat.ID.WINDOWS:
        if info.pic:
            flags.append("-fPIC")
        if info.cfg.hide_symbols:
            flags.append("-fvisibility=hidden")

    flags.append("-m64")

    if info.release:
        flags.extend(["-O3", "-flto", "-ffast-math", "-msse4.2", "-DNDEBUG"])
    else:
        flags.extend(["-O0", "-g", "-Wall", "-Wpedantic", "-Wextra", "-DDEBUG"])

    for [name, val] in info.defines.items():
        if val is not None:
            flags.append(f"-D{name}={val}")
        else:
            flags.append(f"-D{name}")
    flags.append(f"-D_BIP={VERSION_NUM}")

    flags.append(f"--std={info.std}")

    if info.cfg.noexcept:
        flags.append("-fno-exceptions")

    return flags


def _msc_obj_args(info: ObjectInfo) -> list[str]:
    flags = ["/c", str(info.src), f"/Fo{info.out}"]

    for i in info.include:
        flags.append(f"/I{i}")

    if info.release:
        flags.extend(["/O2", "/fp:fast", "/GL", "/DNDEBUG"])
    else:
        flags.extend(["/Od", "/DEBUG", "/W3", "/DDEBUG"])

    for [name, val] in info.defines.items():
        if val is not None:
            flags.append(f"/D{name}={val}")
        else:
            flags.append(f"/D{name}")
    flags.append(f"/D_BIP={VERSION_NUM}")

    if info.is_cpp:
        flags.append("/TP")
    else:
        flags.append("/TC")

    flags.extend([f"/std:{info.std}", "/permissive-"])

    if not info.cfg.noexcept:
        flags.append("/EHsc")

    # some additional flags to bring msvc to the modern day
    flags.extend(["/nologo", "/diagnostics:caret", "/utf-8"])

    if info.release:
        flags.extend(["/link", "/LTCG"])

    return flags


# Determine the flags for compiling an object file given the FlagStyle.
def obj_args(style: FlagStyle, info: ObjectInfo) -> list[str]:
    match style:
        case FlagStyle.GNU:
            return _gnu_obj_args(info)
        case FlagStyle.MSC:
            return _msc_obj_args(info)


# Information to link a shared library or an executable.
@dataclass
class LinkInfo:
    cfg: Config
    # Object files.
    obj: list[Path]
    # Output file.
    out: Path
    # Library search directories.
    lib_dirs: list[Path]
    # Libraries to link against.
    libs: list[str]
    # Build with optimizations?
    release: bool
    # Do we have C++ objects?
    is_cpp: bool
    # Linker override for compilers that support it.
    linker: Optional[str]


def _gnu_lib_args(info: LinkInfo) -> list[str]:
    flags = ["-shared", "-o", str(info.out)]

    for f in info.obj:
        flags.append(str(f))

    for d in info.lib_dirs:
        flags.append(f"-L{d}")

    if plat.native() != plat.ID.WINDOWS:
        flags.append("-Wl,-rpath,\\$ORIGIN")
        if info.cfg.hide_symbols:
            flags.append("-fvisibility=hidden")

    if info.release:
        flags.append("-flto")
    else:
        flags.append("-g")

    if info.linker is not None:
        flags.append(f"-fuse-ld={info.linker}")
    elif plat.native() == plat.ID.WINDOWS:
        flags.append("-fuse-ld=lld-link")

    if info.cfg.noexcept:
        flags.append("-fno-exceptions")

    for l in info.libs:
        flags.append(f"-l{l}")

    return flags


def _msc_lib_args(info: LinkInfo) -> list[str]:
    flags = [f"-Fe{info.out}"]

    for f in info.obj:
        flags.append(str(f))

    if info.release:
        flags.extend(["/MD", "/LD", "/GL"])
    else:
        flags.extend(["/MDd", "/LDd"])

    flags.append("/nologo")

    for l in info.libs:
        flags.append(f"{l}.lib")

    flags.append("/link")

    if info.release:
        flags.append("/LTCG")

    for d in info.lib_dirs:
        flags.append(f"/LIBPATH:{d}")

    return flags


def _gnu_exe_args(info: LinkInfo) -> list[str]:
    flags = ["-o", str(info.out)]

    for f in info.obj:
        flags.append(str(f))

    for d in info.lib_dirs:
        flags.append(f"-L{d}")

    if plat.native() != plat.ID.WINDOWS:
        flags.append("-Wl,-rpath,\\$ORIGIN")

    if info.release:
        flags.extend(["-flto"])
    else:
        flags.extend(["-g"])

    if info.linker is not None:
        flags.append(f"-fuse-ld={info.linker}")
    elif plat.native() == plat.ID.WINDOWS:
        flags.append("-fuse-ld=lld-link")

    if info.cfg.noexcept:
        flags.append("-fno-exceptions")

    for l in info.libs:
        flags.append(f"-l{l}")

    return flags


def _msc_exe_args(info: LinkInfo) -> list[str]:
    flags = [f"-Fe{info.out}"]

    for f in info.obj:
        flags.append(str(f))

    if info.release:
        flags.extend(["/MD", "/GL"])
    else:
        flags.append("/MDd")

    flags.append("/nologo")

    for l in info.libs:
        flags.append(f"{l}.lib")

    flags.append("/link")

    if info.release:
        flags.append("/LTCG")

    for d in info.lib_dirs:
        flags.append(f"/LIBPATH:{d}")

    return flags


# Determine the flags for linking a shared library given the FlagStyle.
def lib_args(style: FlagStyle, info: LinkInfo) -> list[str]:
    match style:
        case FlagStyle.GNU:
            return _gnu_lib_args(info)
        case FlagStyle.MSC:
            return _msc_lib_args(info)


def exe_args(style: FlagStyle, info: LinkInfo) -> list[str]:
    match style:
        case FlagStyle.GNU:
            return _gnu_exe_args(info)
        case FlagStyle.MSC:
            return _msc_exe_args(info)


# Generic information about a C or C++ compiler.
@dataclass
class Compiler:
    # Name of compiler displayed to user.
    name: str
    # C compiler executable. If None, the compiler does not support compiling C.
    c_compiler: Optional[str]
    # C++ compiler executable. If None, the compiler does not support compiling
    # C++.
    cpp_compiler: Optional[str]
    # See FlagStyle.
    style: FlagStyle


# Some commonly used compilers.
KNOWN_COMPILERS = {
    "clang": Compiler("Clang", "clang", "clang++", FlagStyle.GNU),
    "gnu": Compiler("GCC", "gcc", "g++", FlagStyle.GNU),
    "clang-cl": Compiler("clang-cl", "clang-cl", "clang-cl", FlagStyle.MSC),
    "msc": Compiler("MSC", "cl", "cl", FlagStyle.MSC),
}

# Alternate names for compilers.
COMPILER_ALIASES = {"gcc": "gnu", "msvc": "msc"}


# Try to determine which compiler to use based on its name.
def find_compiler(name: str) -> Optional[Compiler]:
    name = name.lower()
    if name in KNOWN_COMPILERS:
        return KNOWN_COMPILERS[name]
    if name in COMPILER_ALIASES:
        return KNOWN_COMPILERS[COMPILER_ALIASES[name]]
    return None


# Check if the given compiler is available in our current environment.
def has_compiler(name: str) -> Optional[Compiler]:
    # print("compiler", name)
    compiler = find_compiler(name)
    if compiler is None:
        # print("  not known")
        return None

    if compiler.c_compiler is not None:
        if which(compiler.c_compiler) is None:
            # print("  C frontend not present")
            return None

    if compiler.cpp_compiler is not None:
        if which(compiler.cpp_compiler) is None:
            # print("  C++ frontend not present")
            return None

    # print("  is OK")
    return compiler


# Determine which compiler to use by default.
def default_compiler() -> Optional[Compiler]:
    option1 = has_compiler("clang")
    if option1 is not None:
        return option1

    match plat.native():
        case plat.ID.LINUX:
            return has_compiler("gnu")
        case plat.ID.WINDOWS:
            return has_compiler("msc")
        case plat.ID.DARWIN:
            return has_compiler("gnu")

    return None
