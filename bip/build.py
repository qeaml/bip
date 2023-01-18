from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
import bip.compiler as compiler
import bip.common as common
import sys

@dataclass
class Info:
  root_dir: Path
  src_dir: Path
  out_dir: Path
  obj_dir: Path
  incl_dirs: list[Path]
  cc: compiler.Compiler
  log: common.Log

  def obj_file(self, src_dir: str, src_file: Path) -> Path:
    return self.obj_dir.joinpath(
      src_file.relative_to(self.src_dir).with_suffix("."+self.cc.obj_ext))

  def exe_file(self, fn: str) -> Path:
    exe = self.out_dir.joinpath(fn)
    if sys.platform.startswith("win"):
      exe = exe.with_suffix(".exe")
    return exe

  def lib_file(self, fn: str) -> Path:
    ext = ".dll" if sys.platform.startswith("win") else ".so"
    return self.out_dir.joinpath(fn).with_suffix(ext)
