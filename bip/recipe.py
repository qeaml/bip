from dataclasses import dataclass
from typing import Any, Optional
from pathlib import Path
from datetime import datetime
import bip.build as build
import bip.component as component
import bip.compiler as compiler
import bip.common as common

@dataclass
class Recipe:
  bld: build.Info
  c_info: compiler.CInfo
  cpp_info: compiler.CPPInfo
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
    incl = [root.joinpath(i) for i in build_data.get("incl", [])]

    c_info = compiler.CInfo.from_dict(build_data.get("c", {}))
    cpp_info = compiler.CPPInfo.from_dict(build_data.get("cpp", {}))

    bld = build.Info(
      root, src, out, obj, incl,
      compiler.COMPILERS[cc], False, log
    )

    components = []
    for cname, cdata in data.items():
      if cname == "build":
        continue

      cout: str
      ctype = component.Type.invalid
      for typename in component.Type.__members__:
        if typename in cdata:
          cout = cdata[typename]
          ctype = component.Type[typename]
          break
      if ctype == component.Type.invalid:
        log.err(f"Invalid recipe: component {cname}: unknown or invalid component type")

      csrc = cdata.get("src", cname)
      libs = cdata.get("libs", [])
      incl_dirs = [Path(i) for i in cdata.get("incl", [])]
      link_args = cdata.get("link", [])

      cc_info = compiler.CInfo.from_dict(cdata.get("c", {}))
      ccpp_info = compiler.CPPInfo.from_dict(cdata.get("cpp", {}))

      components.append(component.Component(
        cname, libs, incl_dirs, link_args, cc_info, ccpp_info, csrc, ctype, cout,
      ))

    return Recipe(bld, c_info, cpp_info, log, components)

  def build(self) -> bool:
    start_time = datetime.now()
    self.bld.log = self.log
    self.bld.out_dir.mkdir(parents=True, exist_ok=True)
    self.bld.obj_dir.mkdir(parents=True, exist_ok=True)
    for c in self.components:
      if not c.should_build(self.bld):
        continue
      if not c.build(self.bld, self.c_info, self.cpp_info):
        self.log.err("Build failed. Aborting")
        return False
    total_time = datetime.now() - start_time
    self.log.verbose(f" === Built all in {total_time}")
    return True
