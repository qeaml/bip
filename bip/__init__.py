from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum
import importlib.util
import json
from os import unlink
from pathlib import Path
import subprocess
import sys
import textwrap
import tomllib
from types import ModuleType
from typing import Any, Optional, Callable
from shutil import copy, copytree, rmtree

g_version = (2, 1)
# version number consists of a nibble representing the major version, then a
# byte representing the minor version and finally a byte representing the patch
# version. for example, 3.2.1 is encoded as 0x30201
g_version_number = g_version[0] * 0x10000 + g_version[1] * 0x100

class Platform(IntEnum):
  Unspecified = -1
  Linux = 0
  Windows = 1
  Darwin = 2

g_platnames = {
  "win": Platform.Windows,
  "win32": Platform.Windows,
  "windows": Platform.Windows,

  "linux": Platform.Linux,
  "unix": Platform.Linux,

  "osx": Platform.Darwin,
  "darwin": Platform.Darwin,
  "mac": Platform.Darwin,
  "macosx": Platform.Darwin,
}

g_platform = Platform.Unspecified
g_verbose = False

def verbose(msg: str) -> None:
  if g_verbose:
    print(msg, file=sys.stdout)

def note(msg: str) -> None:
  print("\x1b[1m" + msg + "\x1b[22m")

def tip(tip: str) -> None:
  note("Tip: " + textwrap.indent(tip, "     ")[5:])

def warn(msg: str, warn_tip = "") -> None:
  print("\x1b[33m" + msg + "\x1b[39m")
  if warn_tip != "":
    tip(warn_tip)

def err(msg: str, err_tip = "") -> None:
  print("\x1b[1m\x1b[31m" + msg + "\x1b[39m\x1b[22m")
  if err_tip != "":
    tip(err_tip)

LOG_MAX_LINE_LEN = 120

def cmd(cmd: str) -> bool:
  if g_verbose:
    note(f"$ {cmd}")
  else:
    log_cmd = cmd
    if len(cmd) >= LOG_MAX_LINE_LEN - 2:
      log_cmd = cmd[:LOG_MAX_LINE_LEN - 5] + "..."
    note(f"$ {log_cmd}")

  return subprocess.run(cmd, shell=True).returncode == 0

def copyfile(src: Path, dst: Path) -> bool:
  if not src.exists():
    warn(f"Cannot copy file {src} because it does not exist")
    return False

  note(f"> {src} -> {dst}")
  copy(src, dst)
  return True

def copydir(src: Path, dst: Path) -> bool:
  if not src.exists():
    warn(f"Cannot copy directory {src} because it does not exist")
    return False
  if dst.exists():
    return True

  note(f"> {src} -> {dst}")
  copytree(src, dst)
  return True

def delete(file: Path) -> None:
  if file.exists():
    note(f"~ {file}")
    unlink(file)

delfile = delete

def deldir(dir: Path) -> None:
  if dir.exists():
    note(f"~ {dir}")
    rmtree(dir)

def link(target: Path, linkname: Path) -> bool:
  if not target.exists():
    warn(f"Cannot create a link to {target} because it does not exist")
    return False
  if linkname.exists():
    return True

  note(f"& {target} <- {linkname}")
  linkname.symlink_to(target, target_is_directory=target.is_dir())
  return True

@dataclass
class Pathes:
  root: Path
  src: Path
  out: Path
  obj: Path

  @classmethod
  def from_dict(cls, root: Path, raw: dict[str, str]) -> Optional["Pathes"]:
    if "src" not in raw:
      err("No source directory!",
        "Add the 'src' key containing the name of the source directory.\n"
        "Source files must be placed in it.")
      return None
    src = root.joinpath(raw["src"])

    if "out" not in raw:
      err("No output directory!",
        "Add the 'out' key containing the name of the output directory.\n"+
        "The final executables & shared libraries will end up in it.")
      return None
    out = root.joinpath(raw["out"])

    if "obj" not in raw:
      err("No object directory!",
        "Add the 'obj' key containing the name of the object directory.\n"+
        "Object files will be placed in it.")
      return None
    obj = root.joinpath(raw["obj"])

    return cls(root, src, out, obj)

  def overrides_from_dict(self, name: str, raw: dict[str, str]) -> "Pathes":
    src_path = [Path(raw["src"])] if "src" in raw else [Path(name)]
    out_path = [Path(raw["out"])] if "out" in raw else []
    obj_path = [Path(raw["obj"])] if "obj" in raw else [Path(name)]
    return Pathes(
      self.root,
      self.src.joinpath(*src_path),
      self.out.joinpath(*out_path),
      self.obj.joinpath(*obj_path),
    )

@dataclass
class CompileCommand:
  directory: Path
  file: Path
  arguments: list[str]
  output: Path

  def to_json(self) -> dict:
    return {
      "directory": str(self.directory),
      "file": str(self.file),
      "arguments": self.arguments,
      "output": str(self.output)
    }

CompileCommands = list[CompileCommand]

class Type(IntEnum):
  invalid = -1
  exe = 0
  lib = 1
  plug = 2
  dep = 3

class Lang(IntEnum):
  invalid = -1
  c = 0
  cpp = 0
  go = 1

class Job(ABC):
  @abstractmethod
  def __init__(self, type: Type, pathes: Pathes, settings: dict[str, str]):
    if not pathes.obj.parent.exists():
      pathes.obj.parent.mkdir(parents=True)
    if not pathes.out.parent.exists():
      pathes.out.parent.mkdir(parents=True)

  @abstractmethod
  def want_build(self) -> bool:
    pass

  @abstractmethod
  def build(self) -> bool:
    pass

  @abstractmethod
  def clean(self) -> None:
    pass

  @abstractmethod
  def compile_commands(self) -> CompileCommands:
    pass

g_opt = False

@dataclass
class CObj:
  class Type(IntEnum):
    C = 0      # use C driver
    CPP = 1    # use C++ driver
    WINRES = 2 # windows resource file

  type: Type
  src: Path
  out: Path

class CJob(Job):
  type: Type
  pathes: Pathes

  _cc: str
  _cppc: str
  _incl: list[str]
  _libs: list[str]
  _link: list[str]
  _cstd: str
  _cppstd: str
  _ld: Optional[str]

  _link_cpp: bool
  _reuse_obj: list[CObj]
  _build_obj: list[CObj]

  def __init__(self, type: Type, pathes: Pathes, settings: dict[str, Any]):
    super(CJob, self).__init__(type, pathes, settings)
    self.type = type
    self.pathes = pathes
    # TODO: figure out a default compiler?
    self._cc = settings.get("cc", "clang")
    self._cppc = settings.get("cppc", "clang++")
    self._incl = settings.get("incl", [])
    self._libs = settings.get("libs", [])
    self._link = settings.get("link", [])
    self._cstd = settings.get("cstd", "c11")
    self._cppstd = settings.get("cppstd", "c++17")

    self._ld = None
    if "ld" in settings:
      self._ld = settings["ld"]
    elif g_platform == Platform.Windows and self._cc == "clang":
      self._ld = "lld-link"

    self._reuse_obj = []
    self._build_obj = []

  _C_EXTS = [".c"]
  _CPP_EXTS = [".cpp", ".cxx", ".cc"]
  _WINRES_EXTS = [".rc"]

  _OBJ_EXTS = {
    CObj.Type.C: ".o",
    CObj.Type.CPP: ".o",
    CObj.Type.WINRES: ".res",
  }

  def _discover_objs(self, root: Path):
    verbose(f"  discovering objects in {root}")
    self._link_cpp = False
    for e in root.iterdir():
      if e.is_dir():
        self._discover_objs(e)

      type = None
      for ext in self._C_EXTS:
        if e.name.endswith(ext):
          type = CObj.Type.C
          break

      if type is None:
        for ext in self._CPP_EXTS:
          if e.name.endswith(ext):
            type = CObj.Type.CPP
            self._link_cpp = True
            break

      if g_platform == Platform.Windows and type is None:
        for ext in self._WINRES_EXTS:
          if e.name.endswith(ext):
            type = CObj.Type.WINRES
            break

      if type is None:
        continue

      out = self.pathes.obj                       \
        .joinpath(e.relative_to(self.pathes.src)) \
        .with_suffix(self._OBJ_EXTS[type])
      if not out.parent.exists():
        out.parent.mkdir(parents=True, exist_ok=True)

      rebuild = False
      if not out.exists():
        rebuild = True
      else:
        obj_time = out.stat().st_mtime
        src_time = e.stat().st_mtime
        rebuild = obj_time < src_time

      if rebuild:
        verbose(f"  {out} needs to be (re)build")
        self._build_obj.append(CObj(type, e, out))
      else:
        verbose(f"  {out} will be reused")
        self._reuse_obj.append(CObj(type, e, out))

  def want_build(self) -> bool:
    self._discover_objs(self.pathes.src)
    return len(self._build_obj) > 0 or not self.pathes.out.exists()

  def _c_flags(self, obj: CObj) -> list[str]:
    flags = []
    if obj.type == CObj.Type.C:
      flags = [self._cc, f"--std={self._cstd}"]
    if obj.type == CObj.Type.CPP:
      flags = [self._cppc, f"--std={self._cppstd}"]
    flags.extend([
      "-c", str(obj.src),
      f"-o{obj.out}",
    ])
    flags.extend([f"-I{incl}" for incl in self._incl])
    flags.append(f"-D_BIP={g_version_number}")
    if g_opt:
      flags.extend(["-DNDEBUG", "-O3"])
    else:
      flags.extend(["-DDEBUG", "-O0", "-g", "-Wall", "-Wpedantic", "-Wextra"])
    if g_platform != Platform.Windows and self.type == Type.lib:
      flags.append("-fPIC")
    return flags

  def _winres_flags(self, obj: CObj) -> list[str]:
    flags = ["rc", "/nologo", "/fo", str(obj.out)]
    for i in self._incl:
      flags.extend(["/i", str(i)])
    flags.append(str(obj.src))
    return flags

  def _build_flags(self, obj: CObj) -> list[str]:
    match obj.type:
      case CObj.Type.C:
        return self._c_flags(obj)
      case CObj.Type.CPP:
        return self._c_flags(obj)
      case CObj.Type.WINRES:
        return self._winres_flags(obj)
    return []

  def build(self) -> bool:
    obj_names = []
    for obj in self._build_obj:
      flags = self._build_flags(obj)
      if not cmd(' '.join(flags)):
        return False
      obj_names.append(str(obj.out))
    obj_names.extend(str(p.out) for p in self._reuse_obj)

    flags = []
    if self._link_cpp:
      flags.append(self._cppc)
    else:
      flags.append(self._cc)
    flags.extend([
      f"-o{self.pathes.out}",
      f"-L{self.pathes.out.parent}",
      *obj_names
    ])
    flags.extend([f"-l{lib}" for lib in self._libs])
    flags.extend([f"-Wl,{arg}" for arg in self._link])
    if self._ld is not None:
      flags.append(f"-fuse-ld={self._ld}")
    if g_opt:
      flags.append("-flto")
    else:
      flags.append("-g")
    if self.type == Type.lib:
      flags.extend(["-shared", "-fPIE"])
    if g_platform != Platform.Windows:
      flags.extend([
        "-rpath", "$$ORIGIN",
        f"-Wl,-rpath-link,{self.pathes.out.parent}"
      ])
    return cmd(' '.join(flags))

  def clean(self) -> None:
    self._discover_objs(self.pathes.src)
    for obj in self._reuse_obj:
      delete(obj.out)
    for bld in self._build_obj:
      delete(bld.out)
    delete(self.pathes.out)

  def compile_commands(self) -> CompileCommands:
    self._discover_objs(self.pathes.src)
    compile_commands = []
    for obj in self._build_obj:
      compile_commands.append(CompileCommand(
        self.pathes.root, obj.src, self._build_flags(obj), obj.out
      ))
    for obj in self._reuse_obj:
      compile_commands.append(CompileCommand(
        self.pathes.root, obj.src, self._build_flags(obj), obj.out
      ))
    return compile_commands

class GoJob(Job):
  type: Type
  pathes: Pathes

  def __init__(self, type: Type, pathes: Pathes, settings: dict[str, str]):
    super(GoJob, self).__init__(type, pathes, settings)
    self.type = type
    self.pathes = pathes

  def want_build(self) -> bool:
    return True # go build does this for us

  def build(self) -> bool:
    buildmode: str
    if self.type == Type.exe:
      buildmode = "exe"
    elif self.type == Type.lib:
      buildmode = "c-shared"

    out = Path().joinpath(*[".." for e in self.pathes.src.parts]).joinpath(self.pathes.out)

    cmd(f"go build -o {out} -C {self.pathes.src} -buildmode={buildmode} .")
    return True

  def clean(self) -> None:
    cmd(f"go clean -C {self.pathes.src}")
    delete(self.pathes.out)

  def compile_commands(self) -> CompileCommands:
    return []

@dataclass
class IPlug:
  _module: ModuleType

  # the two required functions
  ConfigureFn = Callable[[Pathes, dict[str, str]], bool]
  WantRunFn = Callable[[], bool]
  # the optional functions
  RunFn = Callable[[], bool]
  CleanFn = Callable[[], None]
  CompileCommandsFn = Callable[[], list[CompileCommand]]

  configure: ConfigureFn
  run: RunFn

  want_run: Optional[WantRunFn]
  clean: Optional[CleanFn]
  compile_commands: Optional[CompileCommandsFn]

class PlugJob(Job):
  typ: Type
  pathes: Pathes

  _settings: dict[str, str]
  _module: Optional[ModuleType]

  _plug: Optional[IPlug]

  def __init__(self, pathes: Pathes, settings: dict[str, str]):
    super(PlugJob, self).__init__(Type.plug, pathes, settings)
    self.pathes = pathes
    self._settings = settings
    self._plug = None

  def _ensure_module(self) -> bool:
    if self._plug is None:
      mod_path = self.pathes.src.joinpath("plug.py")
      mod_spec = importlib.util.spec_from_file_location("plug", mod_path)
      if mod_spec is None:
        err(f"Could not import '{mod_path}'")
        return False

      module = importlib.util.module_from_spec(mod_spec)
      if module is None:
        err(f"Could not load '{mod_path}'")
        return False
      mod_spec.loader.exec_module(module)

      if not hasattr(module, "configure"):
        err(f"{mod_path} does not define configure(Pathes, dict)")
        return False

      if not hasattr(module, "run"):
        err(f"{mod_path} does not define run()")
        return False

      want_run: Optional[FWantRun] = None
      if hasattr(module, "want_run"):
        want_run = module.want_run

      clean: Optional[FClean] = None
      if hasattr(module, "clean"):
        clean = module.clean

      compile_commands: Optional[FCompileCommands] = None
      if hasattr(module, "compile_commands"):
        compile_commands = module.compile_commands

      self._plug = IPlug(
        module,
        module.configure,
        module.run,
        want_run,
        clean,
        compile_commands
      )
      if not self._plug.configure(self.pathes, self._settings):
        return False

    return True

  def want_build(self) -> bool:
    if not self._ensure_module():
      return False
    if self._plug.want_run is not None:
      return self._plug.want_run()
    return True

  def build(self) -> bool:
    if not self._ensure_module():
      return False
    return self._plug.run()

  def clean(self) -> None:
    if not self._ensure_module():
      return
    if self._plug.clean is not None:
      self._plug.clean()

  def compile_commands(self) -> CompileCommands:
    if not self._ensure_module():
      return []
    if self._plug.compile_commands is not None:
      return self._plug.compile_commands()
    return []

def create_job(out_fn: str, lang: Lang, type: Type, pathes: Pathes, settings: dict[str, str]) -> Optional[Job]:
  prefix = ""
  suffix = ""
  if type == Type.plug:
    return PlugJob(pathes, settings)
  elif type == Type.exe and g_platform == Platform.Windows:
    suffix = ".exe"
  elif type == Type.lib:
    match g_platform:
      case Platform.Windows:
        suffix = ".dll"
      case Platform.Linux:
        prefix = "lib"
        suffix = ".so"
      case Platform.Darwin:
        suffix = ".dylib"

  pathes.obj.mkdir(parents=True, exist_ok=True)
  pathes.out.mkdir(parents=True, exist_ok=True)
  pathes.out = pathes.out.joinpath(prefix + out_fn).with_suffix(suffix)
  if lang == Lang.c or lang == Lang.cpp:
    return CJob(type, pathes, settings)
  if lang == Lang.go:
    return GoJob(type, pathes, settings)
  return None

@dataclass
class Component:
  name: str
  job: Job
  platform: Optional[Platform]

  @classmethod
  def from_dict(cls, name: str, raw: dict[str, str], base_pathes: Pathes, base_lang_settings: dict[str, dict[str, str]]) -> Optional["Component"]:
    out_fn = None
    type = Type.invalid
    for typename in Type.__members__:
      if typename in raw:
        type = Type[typename]
        out_fn = raw[typename]
        raw.pop(typename)
        break
    if out_fn is None:
      err(f"Component {name} does not specify a type!",
        "Setting one of the following keys will decide the type of component.\n"+
        "The value of the key is used as the name of the final product.\n"+
        "  exe - executable\n"+
        "  lib - shared library\n"+
        "  plug - plugin to run at build time")
      return None
    if type == Type.invalid:
      err(f"Component {name} does not specify a type!",
        "Setting one of the following keys will decide the type of component.\n"+
        "The value of the key is used as the name of the final product.\n"+
        "  exe - executable\n"+
        "  lib - shared library\n"+
        "  plug - plugin to run at build time")
      return None

    lang = Lang.invalid
    if type != Type.plug:
      if "lang" not in raw:
        err(f"Component {name} does not specify a language",
          "Set the 'lang' key to one of the following.\n"+
          "  c, cpp, go")
        return None
      lang = Lang[raw["lang"]]
      raw.pop("lang")

    pathes = base_pathes.overrides_from_dict(name if type != Type.plug else out_fn, raw)

    if not pathes.src.exists():
      err("Invalid source path!",
        f"Component {name} has an inexistent source directory: {pathes.src}\n"+
        "Check for any typos. Optionally override the source directory name via the\n"+
        "'src' key.")
      return None

    lang_settings: dict[str, str]
    if lang.name in base_lang_settings:
      lang_settings = base_lang_settings[lang.name] | raw
    else:
      lang_settings = raw

    job = create_job(out_fn, lang, type, pathes, lang_settings)
    if job is None:
      err(f"Invalid job configuration for {name}: {lang.name} {type.name}",
        "This exact combination of langage & component type may not be supported.")
      return None

    plat = None
    if "platform" in raw:
      platname = raw["platform"]
      if platname.lower() in g_platnames:
        plat = g_platnames[platname.lower()]
      else:
        warn(f"Component `{name}` specifies invalid platform restriction: `{platname}`")
        plat = Platform.Unspecified

    return cls(name, job, plat)

@dataclass
class Recipe:
  pathes: Pathes
  components: list[Component]

  @classmethod
  def from_dict(cls, root: Path, raw: dict[str, dict[str, Any]]) -> Optional["Recipe"]:
    if not "build" in raw:
      err("No build section!",
        "Make sure to define a [build] section at the top of your recipe file.\n"+
        "It defines the base paths for all the components.\n"+
        "The following keys are required:\n"
        "  src - the source directory containing each component's source code in an\n"+
        "        accordingly named subdirectory\n"+
        "  out - the directory to place the final executables in\n"+
        "  obj - the directory to place object and other temporary files in")
      return None

    build = raw["build"]
    raw.pop("build")

    lang_settings = {}
    for langname in Lang.__members__:
      if langname in build:
        lang_settings[langname] = build[langname]
        build.pop(langname)

    pathes = Pathes.from_dict(root, build)
    if pathes is None:
      return None

    components = []
    for name, cmpnt_raw in raw.items():
      cmpnt = Component.from_dict(name, cmpnt_raw, pathes, lang_settings)
      if cmpnt is None:
        return None
      if cmpnt.platform is not None:
        if cmpnt.platform != g_platform:
          verbose(f"  ignoring {cmpnt.name} due to platform restriction {cmpnt.platform.name}")
          continue
      components.append(cmpnt)

    return cls(pathes, components)

  def build(self) -> bool:
    for cmpnt in self.components:
      if not cmpnt.job.want_build():
        continue

      note(f"* {cmpnt.name}")
      if not cmpnt.job.build():
        return False

    return True

  def clean(self) -> None:
    for cmpnt in self.components:
      note(f"* {cmpnt.name}")
      cmpnt.job.clean()

  def gencmd(self) -> None:
    compile_commands: list[dict] = []
    for cmpnt in self.components:
      note(f"* {cmpnt.name}")
      cmds = cmpnt.job.compile_commands()
      verbose(f"  has {len(cmds)} commands")
      compile_commands.extend(c.to_json() for c in cmds)

    compile_commands_path = self.pathes.root.joinpath("compile_commands.json")
    mode = "wt" if compile_commands_path.exists() else "xt"

    with compile_commands_path.open(mode) as f:
      json.dump(compile_commands, f)

g_progname = "bip"
g_pos_args = []
g_flags = []
g_params = {}

def help(topic = "") -> int:
  match topic:
    case "":
      note(f"Usage: {g_progname} <action> [project directory] [options...]")
      print(textwrap.dedent(
      # --------------------------------------------------------------------------------
        """
        Where <action> can be one of:
          help - display this message
          ver - check bip's current version
          build - perform a build
          clean - remove any build artifacts
          gencmd - generate compile_commands.json
        """
      ).strip())
      note("You may also use help <topic> for more detailed information.")
      print(textwrap.dedent(
      # --------------------------------------------------------------------------------
        """
        Where <topic> can be one of:
          clean - explains the `clean` action
        """
      ).strip())
    case "clean":
      print(textwrap.dedent(
      # --------------------------------------------------------------------------------
        """
        The `clean` action is used to remove all artifacts from previous builds. For
        example, in a C/C++ project, this would include object files. In case you are
        using plugins to generate code, that generated code is also removed.

        This only deletes files that bip deems to affect the result of the build. All
        other files that may be present in the output directories are ignored.
        """).strip())
    case _:
      err(f"No help for `{topic}` found.")
      return 1

  return 0

def main() -> int:
  from sys import argv
  import platform

  global g_platform
  match platform.system():
    case "Windows":
      g_platform = Platform.Windows
    case "Linux":
      g_platform = Platform.Linux
    case "Darwin":
      g_platform = Platform.Darwin

  global g_verbose
  global g_opt
  global g_progname
  g_progname = argv[0]
  for a in argv[1:]:
    if a.startswith("--"):
      param = a[2:]
      val_idx = param.find("=")
      if val_idx == -1:
        g_flags.append(param)
        continue
      g_params[param[2:val_idx]] = param[val_idx+1:]
      continue

    if a.startswith("-"):
      g_flags.append(a[1:])
      continue

    g_pos_args.append(a)

  g_verbose = "v" in g_flags or "verbose" in g_flags
  g_opt = "o" in g_flags or "opt" in g_flags

  verbose("bip v%d.%d" % g_version)

  if len(g_pos_args) < 1:
    err("No action specified!")
    help()
    return 10

  if g_pos_args[0] == "help":
    if len(g_pos_args) > 1:
      return help(g_pos_args[1])
    return help()

  if g_pos_args[0] == "ver":
    note("bip v2.0")
    print("rewritten to be better then ever!!!!")
    return 0

  recipe_fn = Path("recipe.toml")
  if not recipe_fn.exists():
    err("No recipe file was found!",
      "Ensure there is a `recipe.toml` file in the current working directory.")
    return 1

  raw_recipe: dict[str, Any]
  try:
    with recipe_fn.open("rb") as f:
      raw_recipe = tomllib.load(f)
  except tomllib.TOMLDecodeError as e:
    err(f"Invalid recipe file: {e}",
      "Your recipe file may contain invalid TOML.\n"+
      "In case you need to refresh your memory: https://toml.io/")
    return 2

  recipe = Recipe.from_dict(recipe_fn.parent, raw_recipe)
  if recipe is None:
    return 3

  if g_pos_args[0] == "build":
    if not recipe.build():
      err("Build failed!")
      return 4
    return 0

  if g_pos_args[0] == "clean":
    recipe.clean()
    return 0

  if g_pos_args[0] == "gencmd":
    recipe.gencmd()
    return 0

  err(f"Unknown action {g_pos_args[0]}",
    "bip support the following actions:\n"+
    "  build\n"+
    "  clean - remove any build artifacts\n"+
    "  gencmd - generate compile_commands.json")
  return 10
