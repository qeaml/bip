import os
from colorama import just_fix_windows_console as fix_windows_console
from pathlib import Path
from typing import Optional

import bip.cli as cli
import bip.lang.c as C

from .component.abc import RunInfo
from .recipe import Recipe
from .version import VERSION_STR

USAGE = """
Usage: %s <action> [options...]
Where <action> can be:
    check -> ensure a recipe file is available and is valid
    build -> build the current recipe
    clean -> remove all build artifacts
Where [options...] can be:
    --recipe=<name> -> specify name of recipe file (default `recipe.toml`)
""".strip()

MAX_RECIPE_SEARCH_DEPTH = 5


def _find_recipe_file(filename: str) -> Optional[Path]:
    path = Path(filename).resolve()
    for i in range(MAX_RECIPE_SEARCH_DEPTH):
        if path.exists():
            # print(f"recipe file is {path}")
            return path
        path = path.parent.parent / filename
    return None

def main(args: list[str]) -> int:
    fix_windows_console()

    args = cli.parse(args)

    if len(args.pos) < 1:
        print(USAGE % args.program)
        return 1

    match args.pos[0].lower():
        case "version":
            print(VERSION_STR)
            return 0
        case "c-info":
            res = True
            if "all" in args.flags:
                C.show_all_compilers()
            else:
                res = C.show_compiler_info()
            return 0 if res else 1

    recipe_filename = "recipe.toml"
    if "recipe" in args.named:
        recipe_filename = args.named.pop("recipe")

    recipe_path = _find_recipe_file(recipe_filename)
    if recipe_path is None:
        print("Could not find a recipe.")
        print(USAGE % args.program)
        return 1

    is_release = any((x in args.flags for x in ("o", "opt", "r", "rel", "release")))
    info = RunInfo(is_release)

    recipe = Recipe.load(recipe_path, info)
    if recipe is None:
        cli.error("Could not load recipe file.")
        return 2

    os.chdir(recipe_path.parent)

    match args.pos[0].lower():
        case "check":
            print(f"Recipe file {recipe_path} is valid.")
            return 0

        case "clean":
            for c in recipe.components:
                c.clean()
            return 0
        case "build":
            for c in recipe.components:
                if c.want_run():
                    if not c.run(info):
                        return 3
            return 0
        case _:
            print(USAGE % args.program)
            return 1


def script_main() -> int:
    from sys import argv

    old_cwd = os.getcwd()
    status = main(argv)
    os.chdir(old_cwd)
    return status


if __name__ == "__main__":
    exit(script_main)
