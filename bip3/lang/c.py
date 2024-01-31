"""
C and C++ language support.
"""

from dataclasses import dataclass
from enum import IntEnum, auto
from pathlib import Path
from shutil import which
from typing import Optional
import bip3.platform


# CLI argument style for compiler invocations. This also decides the object file
# extension.
class FlagStyle(IntEnum):
    # similar to GCC,G++
    GNU = auto()
    # similar to CL.EXE
    MSC = auto()


# Information to compile an object file.
@dataclass
class ObjectInfo:
    # Source file.
    src: Path
    # Output object file.
    out: Path
    # Include directories.
    include: list[Path]
    # Build with optimizations?
    optimized: bool
    # Extra preprocessor defines.
    defines: dict[str, Optional[str]]
    # Is this a C++ file?
    is_cpp: bool
    # Which C/C++ standard to use.
    std: str


def _gnu_obj_args(info: ObjectInfo) -> list[str]:
    flags = ["-c", str(info.src), "-o", str(info.out)]

    for i in info.include:
        flags.append(f"-I{i}")

    if info.optimized:
        flags.extend(["-O3", "-DNDEBUG=1"])
    else:
        flags.extend(["-O0", "-g", "-Wall", "-Wpedantic", "-Wextra", "-DDEBUG=1"])

    for [name, val] in info.defines.items():
        if val is not None:
            flags.append(f"-D{name}={val}")
        else:
            flags.append(f"-D{name}")

    if info.is_cpp:
        flags.append("-xc++")
    else:
        flags.append("-xc")

    flags.append(f"--std={info.std}")

    return []


def _msc_obj_args(info: ObjectInfo) -> list[str]:
    flags = ["/c", str(info.src), f"/Fo{info.out}"]

    for i in info.include:
        flags.append(f"/I{i}")

    if info.optimized:
        flags.extend(["/O2", "/DNDEBUG=1"])
    else:
        flags.extend(["/Od", "/DEBUG", "/Wall", "/DDEBUG=1"])

    for [name, val] in info.defines.items():
        if val is not None:
            flags.append(f"/D{name}={val}")
        else:
            flags.append(f"/D{name}")

    if info.is_cpp:
        flags.append("/TP")
    else:
        flags.append("/TC")

    flags.extend([f"/std:{info.std}", "/permissive-"])

    # some additional flags to bring msvc to the modern day
    flags.extend(["/nologo", "/diagnostics:caret", "/external:anglebrackets", "/utf-8"])

    return []


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
    # Object files.
    obj: list[Path]
    # Output file.
    out: Path
    # Library search directories.
    lib_dirs: list[Path]
    # Libraries to link against.
    libs: list[str]
    # Build with optimizations?
    optimized: bool
    # Do we have C++ objects?
    is_cpp: bool
    # Linker override for compilers that support it.
    linker: Optional[str]


def _gnu_lib_args(info: LinkInfo) -> list[str]:
    flags = ["-o", str(info.out)]

    for f in info.obj:
        flags.append(str(f))

    for d in info.lib_dirs:
        flags.append(f"-L{d}")

    if info.optimized:
        flags.append("-flto")

    if info.linker is not None:
        flags.append(f"-fuse-ld={info.linker}")

    for l in info.libs:
        flags.append(f"-l{l}")

    return flags


def _msc_lib_args(info: LinkInfo) -> list[str]:
    flags = [f"-Fe{info.out}"]

    for f in info.obj:
        flags.append(str(f))

    if info.optimized:
        flags.append("/LD")
    else:
        flags.append("/LDd")

    for l in info.libs:
        flags.append(f"{l}.lib")

    flags.append("/link")

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


# Generic information about a C or C++ compiler.
@dataclass
class Compiler:
    # C compiler executable. If None, the compiler does not support compiling C.
    c_compiler: Optional[str]
    # C++ compiler executable. If None, the compiler does not support compilig
    # C++.
    cpp_compiler: Optional[str]
    # See FlagStyle.
    style: FlagStyle


# Some commonly used compilers.
KNOWN_COMPILERS = {
    "clang": Compiler("clang", "clang++", FlagStyle.GNU),
    "gnu": Compiler("gcc", "g++", FlagStyle.GNU),
    "msc": Compiler("cl", "cl", FlagStyle.MSC),
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
    compiler = find_compiler(name)
    if compiler is None:
        return None

    if compiler.c_compiler is not None:
        if which(compiler.c_compiler) is None:
            return None

    if compiler.cpp_compiler is not None:
        if which(compiler.cpp_compiler) is None:
            return None

    return compiler


# Determine which compiler to use by default.
def default_compiler() -> Optional[Compiler]:
    option1 = has_compiler("clang")
    if option1 is not None:
        return option1

    match platform.native():
        case platform.ID.LINUX:
            return has_compiler("gnu")
        case platform.ID.WINDOWS:
            return has_compiler("msc")
        case platform.ID.DARWIN:
            return has_compiler("gnu")

    return None
