from dataclasses import dataclass
from typing import Any, Optional
from pathlib import Path
import build
import component
import compiler
import common

@dataclass
class Recipe:
  bld: build.Info
  log: common.Log
  components: list[component.Component]

  @classmethod
  def from_dict(cls, log: common.Log, root: Path, data: dict[str, Any]) -> Optional["Recipe"]:
    if "build" not in data:
      log.err("Invalid recipe: no 'build' table")
      return None

    build_data = data["build"]
    if "cc" not in build_data:
      log.err("Invalid recipe: build table does not contain 'cc' key")
      return None

    cc = build_data["cc"]
    if cc not in compiler.COMPILERS:
      log.err(f"Invalid recipe: unknown compiler '{cc}'")
      return None

    src = root.joinpath(build_data.get("src", ""))
    out = root.joinpath(build_data.get("out", ""))
    obj = root.joinpath(build_data.get("obj", ""))

    bld = build.Info(
      root, src, out, obj,
      compiler.COMPILERS[cc], log
    )

    components = []
    for cname, cdata in data.items():
      if cname == "build":
        continue

      if "exe" not in cdata and "lib" not in cdata:
        log.err(f"Invalid recipe: component {cname}: must specify either 'exe' or 'lib'")
        return None

      is_exe = "exe" in cdata
      if is_exe and "lib" in cdata:
        log.err(f"Invalid recipe: component {cname}: cannot specify both 'exe' and 'lib' at the same time")
        return None

      csrc = cdata.get("src", cname)
      cout = cdata["exe"] if is_exe else cdata["lib"]
      libs = cdata.get("libs", [])
      incl_dirs = [Path(i) for i in cdata.get("incl", [])]

      components.append(component.Component(
        cname, libs, incl_dirs, csrc, is_exe, cout,
      ))

    return Recipe(bld, log, components)

  def build(self) -> bool:
    self.bld.out_dir.mkdir(parents=True, exist_ok=True)
    self.bld.obj_dir.mkdir(parents=True, exist_ok=True)
    for c in self.components:
      if not c.should_build(self.bld, self.log):
        continue
      if not c.build(self.bld, self.log):
        self.log.err("Build failed. Aborting")
        return False
    return True
