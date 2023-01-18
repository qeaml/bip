from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
import bip.common as common
import subprocess

C_EXTS = ["c"]
CPP_EXTS = ["cpp", "cxx", "cc"]

@dataclass
class CPPInfo:
  std: str

  @classmethod
  def from_dict(cls, data: dict[str, str]) -> "CPPInfo":
    std = data.get("std", "c++17")

    return cls(std)

@dataclass
class CInfo:
  std: str

  @classmethod
  def from_dict(cls, data: dict[str, str]) -> "CInfo":
    std = data.get("std", "c11")

    return cls(std)

@dataclass
class Info:
  incl: list[Path]
  libs: list[str]
  link: list[str]
  log: common.Log

  c = CInfo("c11")
  cpp = CPPInfo("c++17")

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

  @property
  def obj_ext(self) -> str:
    return "o"

  def compile_obj(self, inf: Info, src: Path, out: Path) -> bool:
    flags = ["-c", "-flto", f"{src}", "-o", f"{out}"]

    if src.suffix.removeprefix(".") in C_EXTS:
      flags.extend(["-xc", f"--std={inf.c.std}"])
    if src.suffix.removeprefix(".") in CPP_EXTS:
      flags.extend(["-xc++", f"--std={inf.cpp.std}"])

    for i in inf.incl:
      flags.append(f"-I{i}")

    cmd = self._cmd + " " + " ".join(flags)
    inf.log.verbose(cmd)
    return subprocess.run(cmd).returncode == 0
    # return True

  def build_exe(self, inf: Info, objs: list[Path], out: Path) -> bool:
    flags = ["-flto", f"-L{out.parent}", "-o", f"{out}"]
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
    flags = ["-fPIC", "-flto", "-shared", f"-L{out.parent}", "-o", f"{out}"]
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

class MSVC(Compiler):
  _CMD_BASE = "CL /nologo "

  @property
  def obj_ext(self) -> str:
    return "obj"

  def compile_obj(self, inf: Info, src: Path, out: Path) -> bool:
    flags = ["/c", f"/Fo{out}"]

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
