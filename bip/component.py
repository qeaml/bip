from pathlib import Path
from typing import Tuple
from datetime import datetime
from enum import Enum
from typing import Optional
from types import ModuleType
import sys
import importlib.util
import bip.build as build
import bip.compiler as compiler
import bip.common as common

class Type(Enum):
  invalid = -1
  exe = 0
  lib = 1
  plug = 2

class Component:
  _SRC_EXTS = ["c", "cpp"]

  name: str
  libs: list[str]
  incl_dirs: list[Path]
  link_args: list[str]
  c_info: compiler.CInfo
  cpp_info: compiler.CPPInfo
  src_dir: str
  type: Type
  out_fn: str

  # source files that needs to be rebuilt on next build() call
  #                    src   obj
  _rebuild: list[Tuple[Path, Path]]
  # objects that are up-to-date
  #            obj
  _built: list[Path]
  # plugin package
  _plug: Optional[ModuleType]

  def __init__(self,
    name: str, libs: list[str], incl_dirs: list[Path], link_args: list[str],
    c_info: compiler.CInfo, cpp_info: compiler.CPPInfo,
    src_dir: str, type: Type, out_fn: str,
  ):
    self.name = name
    self.libs = libs
    self.incl_dirs = incl_dirs
    self.link_args = link_args
    self.c_info = c_info
    self.cpp_info = cpp_info
    self.src_dir = src_dir
    self.type = type
    self.out_fn = out_fn

    self._plug = None
    self._rebuild = []
    self._built = []

  def _gather_objects(self, bld: build.Info) -> bool:
    self._rebuild = []
    self._built = []

    src = bld.src_dir.joinpath(self.src_dir)
    if not src.exists():
      bld.log.err(f"Source directory {src.absolute()} does not exist")
      return False

    out = bld.obj_dir.joinpath(self.src_dir)
    if not out.exists():
      out.parent.mkdir(exist_ok=True, parents=True)

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

    return True

  def _should_build(self, bld: build.Info) -> bool:
    bld.log.verbose(f"Checking if {self.name} should be rebuilt...")

    if not self._gather_objects(bld):
      return False

    final_file: Path
    if self.type == Type.exe:
      final_file = bld.exe_file(self.out_fn)
    else:
      final_file = bld.lib_file(self.out_fn)

    bld.log.verbose(f"{len(self._rebuild)} source(s) need to be rebuilt")
    if not final_file.exists():
      bld.log.verbose("Output file does not exist")
      return True
    return len(self._rebuild) > 0

  def _clean(self, bld: build.Info) -> bool:
    if not self._gather_objects(bld):
      return False
    for f in self._built:
      bld.log.verbose(f"Removing: {f}")
      f.unlink(missing_ok=True)
    for _, f in self._rebuild:
      bld.log.verbose(f"Removing: {f}")
      f.unlink(missing_ok=True)
    return True

  def _build(self, bld: build.Info, c_info: compiler.CInfo, cpp_info: compiler.CPPInfo) -> bool:
    if bld.opt:
      bld.log.verbose("Building WITH optimizations.")
    else:
      bld.log.verbose("Building WITHOUT optimizations.")

    start_time = datetime.now()

    objs = self._built
    incl = self.incl_dirs
    incl.extend(bld.incl_dirs)
    obj_info = compiler.Info(
      incl, [],
      self.link_args, bld.opt, bld.log,
      c_info.merge(self.c_info),
      cpp_info.merge(self.cpp_info))
    for src_file, obj_file in self._rebuild:
      bld.log.verbose(f"Building object {obj_file} from {src_file}")
      obj_file.parent.mkdir(exist_ok=True, parents=True)
      if not bld.cc.compile_obj(obj_info, src_file, obj_file):
        return False
      objs.append(obj_file)

    final_file: Path
    if self.type == Type.exe:
      final_file = bld.exe_file(self.out_fn)
    else:
      final_file = bld.lib_file(self.out_fn)
    final_file.parent.mkdir(exist_ok=True, parents=True)
    final_info = compiler.Info(
      [], self.libs,
      self.link_args, bld.opt, bld.log,
      c_info.merge(self.c_info),
      cpp_info.merge(self.cpp_info))
    bld.log.verbose(f"Building executable {final_file} from:")
    for o in objs:
      bld.log.verbose(f"  - {o}")
    ok: bool
    if self.type == Type.exe:
      ok = bld.cc.build_exe(final_info, objs, final_file)
    else:
      ok = bld.cc.build_lib(final_info, objs, final_file)
    total_time = datetime.now() - start_time
    bld.log.verbose(f" -- Built in {total_time}")
    return ok

  def _ensure_plug(self, bld: build.Info) -> bool:
    if self._plug is None:
      mod_path = bld.src_dir.joinpath(self.out_fn, "plug.py")
      mod_spec = importlib.util.spec_from_file_location("plug", mod_path)
      if mod_spec is None:
        bld.log.err(f"Plugin {self.name}: could not import module '{self.out_fn}'")
        return False

      self._plug = importlib.util.module_from_spec(mod_spec)
      mod_spec.loader.exec_module(self._plug) # type: ignore

    return True

  def should_build(self, bld: build.Info) -> bool:
    if self.type == Type.plug:
      if not self._ensure_plug(bld):
        return False
      return self._plug.should_build(bld) # type: ignore
    return self._should_build(bld)

  def clean(self, bld: build.Info) -> bool:
    if self.type == Type.plug:
      if not self._ensure_plug(bld):
        return False
      return self._plug.clean(bld) # type: ignore
    return self._clean(bld)

  def build(self, bld: build.Info, c_info: compiler.CInfo, cpp_info: compiler.CPPInfo) -> bool:
    if self.type == Type.plug:
      return self._plug.build(bld) # type: ignore
    return self._build(bld, c_info, cpp_info)
