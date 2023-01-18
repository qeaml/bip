from pathlib import Path
from typing import Tuple
import bip.build as build
import bip.compiler as compiler
import bip.common as common

class Component:
  _SRC_EXTS = ["c", "cpp"]

  name: str
  libs: list[str]
  incl_dirs: list[Path]
  link_args: list[str]
  src_dir: str
  is_exe: bool
  out_fn: str

  # source files that needs to be rebuilt on next build() call
  #                    src   obj
  _rebuild: list[Tuple[Path, Path]]
  # objects that are up-to-date
  #            obj
  _built: list[Path]

  def __init__(self,
    name: str, libs: list[str], incl_dirs: list[Path], link_args: list[str],
    c_info: compiler.CInfo, cpp_info: compiler.CPPInfo,
    src_dir: str, is_exe: bool, out_fn: str,
  ):
    self.name = name
    self.libs = libs
    self.incl_dirs = incl_dirs
    self.link_args = link_args
    self.src_dir = src_dir
    self.is_exe = is_exe
    self.out_fn = out_fn

    self._rebuild = []
    self._built = []

  def should_build(self, bld: build.Info, log: common.Log) -> bool:
    log.verbose(f"Checking if {self.name} should be rebuilt...")

    self._rebuild = []
    self._built = []

    src = bld.src_dir.joinpath(self.src_dir)
    if not src.exists():
      log.err(f"Source directory {src.absolute()} does not exist")
      return False

    out = bld.obj_dir.joinpath(self.src_dir)
    if not out.exists():
      out.mkdir(exist_ok=True)

    for src_file in src.rglob("*"):
      if src_file.is_dir():
        continue
      if src_file.suffix.removeprefix(".") not in Component._SRC_EXTS:
        continue

      obj_file = bld.obj_file(self.src_dir, src_file)
      if (not obj_file.exists()) or obj_file.stat().st_mtime < src_file.stat().st_mtime:
        self._rebuild.append((src_file, obj_file))
      else:
        self._built.append(obj_file)

    final_file: Path
    if self.is_exe:
      final_file = bld.exe_file(self.out_fn)
    else:
      final_file = bld.lib_file(self.out_fn)

    log.verbose(f"{len(self._rebuild)} source(s) need to be rebuilt")
    if not final_file.exists():
      log.verbose("Output file does not exist")
      return True
    return len(self._rebuild) > 0

  def build(self, bld: build.Info, log: common.Log) -> bool:
    objs = self._built
    obj_info = compiler.Info(self.incl_dirs, [], self.link_args, log)
    for src_file, obj_file in self._rebuild:
      log.verbose(f"Building object {obj_file} from {src_file}")
      if not bld.cc.compile_obj(obj_info, src_file, obj_file):
        return False
      objs.append(obj_file)

    final_file: Path
    if self.is_exe:
      final_file = bld.exe_file(self.out_fn)
    else:
      final_file = bld.lib_file(self.out_fn)
    final_info = compiler.Info([], self.libs, self.link_args, log)
    log.verbose(f"Building executable {final_file} from:")
    for o in objs:
      log.verbose(f"  - {o}")
    if self.is_exe:
      return bld.cc.build_exe(final_info, objs, final_file)
    else:
      return bld.cc.build_lib(final_info, objs, final_file)
