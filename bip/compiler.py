from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
import common
import subprocess

class Compiler(ABC):
  @property
  @abstractmethod
  def obj_ext(self) -> str:
    pass

  @abstractmethod
  def compile_obj(self, log: common.Log, incl: list[Path], src: Path, out: Path) -> bool:
    pass

  @abstractmethod
  def build_exe(self, log: common.Log, objs: list[Path], libs: list[str], out: Path) -> bool:
    pass

  @abstractmethod
  def build_lib(self, log: common.Log, objs: list[Path], libs: list[str], out: Path) -> bool:
    pass

class GNULike(Compiler):
  _cmd: str

  def __init__(self, cmd: str):
    self._cmd = cmd

  @property
  def obj_ext(self) -> str:
    return "o"

  def compile_obj(self, log: common.Log, incl: list[Path], src: Path, out: Path) -> bool:
    flags = ["-c", "-flto", f"{src}", "-o", f"{out}"]
    for i in incl:
      flags.append(f"-I{i}")
    cmd = self._cmd + " " + " ".join(flags)
    log.verbose(cmd)
    return subprocess.run(cmd).returncode == 0
    # return True

  def build_exe(self, log: common.Log, objs: list[Path], libs: list[str], out: Path) -> bool:
    flags = ["-flto", "-o", f"{out}"]
    for o in objs:
      flags.append(f"{o}")
    for l in libs:
      flags.append(f"-l{l}")
    cmd = self._cmd + " " + " ".join(flags)
    log.verbose(cmd)
    return subprocess.run(cmd).returncode == 0
    # return True

  def build_lib(self, log: common.Log, objs: list[Path], libs: list[str], out: Path) -> bool:
    flags = ["-fPIC", "-flto", "-shared", "-o", f"{out}"]
    for o in objs:
      flags.append(f"{o}")
    for l in libs:
      flags.append(f"-l{l}")
    cmd = self._cmd + " " + " ".join(flags)
    log.verbose(cmd)
    return subprocess.run(cmd).returncode == 0
    # return True

class MSVC(Compiler):
  _CMD_BASE = "CL /nologo "

  @property
  def obj_ext(self) -> str:
    return "obj"

  def compile_obj(self, log: common.Log, incl: list[Path], src: Path, out: Path) -> bool:
    flags = ["/c", f"/Fo{out}"]
    for i in incl:
      flags.append(f"/I{i}")
    flags.append(str(src))
    cmd = MSVC._CMD_BASE + " ".join(flags)
    log.verbose(cmd)
    return subprocess.run(cmd).returncode == 0

  def build_exe(self, log: common.Log, objs: list[Path], libs: list[str], out: Path) -> bool:
    flags = [f"/Fe{out}"]
    for o in objs:
      flags.append(str(o))
    for l in libs:
      flags.append(f"{l}.lib")
    flags.append(f"/link /LIBPATH:{out.parent}")
    cmd = MSVC._CMD_BASE + " ".join(flags)
    log.verbose(cmd)
    return subprocess.run(cmd).returncode == 0

  def build_lib(self, log: common.Log, objs: list[Path], libs: list[str], out: Path) -> bool:
    flags = ["/LD", f"/Fe{out}"]
    for o in objs:
      flags.append(str(o))
    for l in libs:
      flags.append(f"{l}.lib")
    flags.append(f"/link /LIBPATH:{out.parent}")
    cmd = MSVC._CMD_BASE + " ".join(flags)
    log.verbose(cmd)
    return subprocess.run(cmd).returncode == 0

COMPILERS = {
  "clang": GNULike("clang"),
  "msvc": MSVC(),
}
