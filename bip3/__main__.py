from pathlib import Path
from typing import Optional

import cli
from version import version_str
from recipe import Recipe

USAGE = """
Usage: %s <action> [options...]
Where <action> can be:
    check -> ensure a recipe file is available and is valid
    build -> build the current recipe
    clean -> remove all build artifacts
""".strip()

MAX_RECIPE_SEARCH_DEPTH = 7


def _find_recipe_file() -> Optional[Path]:
    path = Path("recipe.toml").resolve()
    for i in range(MAX_RECIPE_SEARCH_DEPTH):
        if path.exists():
            return path
        path = path.parent.parent / "recipe.toml"
    return None


def main(args: list[str]) -> int:
    args = cli.parse(args)

    if len(args.pos) < 1:
        print(USAGE % args.program)
        return 1

    recipe_path = _find_recipe_file()
    if recipe_path is None:
        print(USAGE % args.program)
        return 1

    recipe = Recipe.load(recipe_path)
    if recipe is None:
        cli.error("Could not load recipe file.")
        return 2

    recipe.optimized = "opt" in args.flags

    match args.pos[0].lower():
        case "check":
            print(f"Recipe file {recipe_path} is valid.")
            return 0
        case "version":
            print(version_str())
            return 0
        case "clean":
            for c in recipe.components:
                c.clean()
            return 0
        case "build":
            for c in recipe.components:
                if c.want_run():
                    if not c.run():
                        return 3
            return 0
        case _:
            print(USAGE % args.program)
            return 1


if __name__ == "__main__":
    from sys import argv

    exit(main(argv))
