from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
import bip.common as common
import subprocess
import sys

C_EXTS = ["c"]
CPP_EXTS = ["cpp", "cxx", "cc"]

@dataclass
class CPPInfo:
  std: str

  @classmethod
  def from_dict(cls, data: dict[str, str]) -> "CPPInfo":
    std = data.get("std", "")
    return cls(std)

  def merge(self, other: "CPPInfo") -> "CPPInfo":
    std = other.std if other.std != "" else self.std if self.std != "" else "c11"
    return CPPInfo(std)

@dataclass
class CInfo:
  std: str

  @classmethod
  def from_dict(cls, data: dict[str, str]) -> "CInfo":
    std = data.get("std", "")
    return cls(std)

  def merge(self, other: "CInfo") -> "CInfo":
    std = other.std if other.std != "" else self.std if self.std != "" else "c11"
    return CInfo(std)

@dataclass
class Info:
  incl: list[Path]
  libs: list[str]
  link: list[str]
  opt: bool
  is_lib: bool
  log: common.Log

  c: CInfo
  cpp: CPPInfo

class Compiler(ABC):
  @property
  @abstractmethod
  def obj_ext(self) -> str:
    pass

  @abstractmethod
  def compile_obj(self, inf: Info, src: Path, out: Path) -> bool:
    pass

  @abstractmethod
  def build_exe(self, inf: Info, objs: list[Path], out: Path) -> bool:
    pass

  @abstractmethod
  def build_lib(self, inf: Info, objs: list[Path], out: Path) -> bool:
    pass

class GNULike(Compiler):
  _cmd: str

  def __init__(self, cmd: str):
    self._cmd = cmd

  def _linker(self) -> str:
    if self._cmd == "clang" and sys.platform.startswith("win"):
      return "lld-link"
    return ""

  @property
  def obj_ext(self) -> str:
    return "o"

  def compile_obj(self, inf: Info, src: Path, out: Path) -> bool:
    flags = ["-D_BIPBUILD_", "-c", "-o", f"{out}"]

    if inf.is_lib:
      flags.append("-fPIC")

    if inf.opt:
      flags.extend(["-DNDEBUG", "-O3"])
    else:
      flags.extend(["-DDEBUG", "-O0", "-glldb", "-Wall", "-Wpedantic", "-Wextra"])

    if src.suffix.removeprefix(".") in C_EXTS:
      flags.extend(["-xc", f"--std={inf.c.std}"])
    if src.suffix.removeprefix(".") in CPP_EXTS:
      flags.extend(["-xc++", f"--std={inf.cpp.std}"])

    for i in inf.incl:
      flags.append(f"-I{i}")

    flags.append(f"{src}")

    cmd = self._cmd + " " + " ".join(flags)
    inf.log.verbose(cmd)
    return subprocess.run(cmd, shell=True).returncode == 0
    # return True

  def build_exe(self, inf: Info, objs: list[Path], out: Path) -> bool:
    flags = [f"-L{out.parent}", "-o", f"{out}"]

    if (linker := self._linker()) != "":
      flags.append(f"-fuse-ld={linker}")

    if inf.opt:
      flags.append("-flto")
    else:
      flags.append("-g")

    if len(inf.link) > 0:
      flags.append("-Wl," + ",".join(inf.link))
    for o in objs:
      flags.append(f"{o}")
    for l in inf.libs:
      flags.append(f"-l{l}")
    cmd = self._cmd + " " + " ".join(flags)
    inf.log.verbose(cmd)
    return subprocess.run(cmd).returncode == 0
    # return True

  def build_lib(self, inf: Info, objs: list[Path], out: Path) -> bool:
    flags = ["-fPIC", "-shared", f"-L{out.parent}", "-o", f"{out}"]

    if (linker := self._linker()) != "":
      flags.append(f"-fuse-ld={linker}")

    if inf.opt:
      flags.append("-flto")
    else:
      flags.append("-g")

    if len(inf.link) > 0:
      flags.append("-Wl," + ",".join(inf.link))
    for o in objs:
      flags.append(f"{o}")
    for l in inf.libs:
      flags.append(f"-l{l}")
    cmd = self._cmd + " " + " ".join(flags)
    inf.log.verbose(cmd)
    return subprocess.run(cmd, shell=True).returncode == 0
    # return True

class MSVC(Compiler):
  _CMD_BASE = "CL /nologo "

  @property
  def obj_ext(self) -> str:
    return "obj"

  def compile_obj(self, inf: Info, src: Path, out: Path) -> bool:
    flags = ["/D_BIPBUILD_", "/c", f"/Fo{out}"]
    if inf.opt:
      flags.extend(["/DNDEBUG", "/Ot"])
    else:
      flags.extend(["/DDEBUG", "/Od /RTC1 /sdl /Wall"])

    if src.suffix.removeprefix(".") in C_EXTS:
      flags.extend(["/TC", f"/std:{inf.c.std}"])
    if src.suffix.removeprefix(".") in CPP_EXTS:
      flags.extend(["/TP", f"/std:{inf.cpp.std}"])

    for i in inf.incl:
      flags.append(f"/I{i}")
    flags.append(str(src))

    cmd = MSVC._CMD_BASE + " ".join(flags)
    inf.log.verbose(cmd)
    return subprocess.run(cmd).returncode == 0

  def build_exe(self, inf: Info, objs: list[Path], out: Path) -> bool:
    flags = [f"/Fe{out}"]
    for o in objs:
      flags.append(str(o))
    for l in inf.libs:
      flags.append(f"{l}.lib")
    flags.append(f"/link /LIBPATH:{out.parent}")
    flags.extend(inf.link)
    cmd = MSVC._CMD_BASE + " ".join(flags)
    inf.log.verbose(cmd)
    return subprocess.run(cmd).returncode == 0

  def build_lib(self, inf: Info, objs: list[Path], out: Path) -> bool:
    flags = ["/LD", f"/Fe{out}"]
    for o in objs:
      flags.append(str(o))
    for l in inf.libs:
      flags.append(f"{l}.lib")
    flags.append(f"/link /LIBPATH:{out.parent}")
    flags.extend(inf.link)
    cmd = MSVC._CMD_BASE + " ".join(flags)
    inf.log.verbose(cmd)
    return subprocess.run(cmd).returncode == 0

COMPILERS = {
  "clang": GNULike("clang"),
  "msvc": MSVC(),
}
