from sys import argv
from pathlib import Path
from cli import *

def main() -> int:
  action = "build"
  root_dir = "."
  verbose = False
  if len(argv) > 1:
    action = argv[1]
  if len(argv) > 2:
    root_dir = argv[2]
  if len(argv) > 3:
    for a in argv:
      if not a.startswith("--"):
        continue
      if a[2:] == "verbose":
        verbose = True

  log = common.Log(verbose)

  root = Path(root_dir)
  if not root.exists():
    log.err("Invalid project. Root directory does not exist.")
    return -1

  match action:
    case "build":
      return build(root, log)
    case _:
      log.err(f"Unknown action: {action}")
      return -2

if __name__ == "__main__":
  exit(main())
