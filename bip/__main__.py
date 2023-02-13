from sys import argv
from pathlib import Path
from .cli import *
import bip.common as common

HELP_MESSAGE = """
Actions:
  build [dir] - build the project at [dir] or current working directory
  clean [dir] - clean files output by previous build at [dir] or current working
                directory
""".strip()

def main() -> int:
  args = Args([], {})

  for a in argv[1:]:
    if a.startswith("--"):
      name, *values = a[2:].split("=")
      args.named[name] = "=".join(values)
    else:
      args.pos.append(a)

  if len(args.pos) < 1:
    print(f"Usage: {argv[0]} <action> ...")
    print(HELP_MESSAGE)
    return -3

  root_dir = "."
  if len(args.pos) > 1:
    root_dir = args.pos[1]

  log = common.Log("verbose" in args.named)
  root = Path(root_dir)
  if not root.exists():
    log.err("Invalid project. Root directory does not exist.")
    return -1

  action = args.pos[0]
  match action:
    case "build":
      return build(args, root, log)
    case "clean":
      return clean(args, root, log)
    case _:
      log.err(f"Unknown action: {action}")
      return -2

if __name__ == "__main__":
  exit(main())
