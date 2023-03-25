from pathlib import Path
from .recipe import Recipe
import tomllib
import bip.common as common
from dataclasses import dataclass

@dataclass
class Args:
  pos: list[str]
  named: dict[str, str]

def build(args: Args, root: Path, log: common.Log) -> int:
  recipe_file = root.joinpath("recipe.toml")
  if not recipe_file.exists():
    log.err("Not a valid project. No recipe file was found.")
    return 1

  recipe_data = {}
  with recipe_file.open("rb") as f:
    recipe_data = tomllib.load(f)

  recipe = Recipe.from_dict(log, root, recipe_data)
  if recipe is None:
    return 2
  recipe.bld.opt = "opt" in args.named

  if not recipe.build():
    return 3

  return 0

def clean(args: Args, root: Path, log: common.Log) -> int:
  recipe_file = root.joinpath("recipe.toml")
  if not recipe_file.exists():
    log.err("Not a valid project. No recipe file was found.")
    return 1

  recipe_data = {}
  with recipe_file.open("rb") as f:
    recipe_data = tomllib.load(f)

  recipe = Recipe.from_dict(log, root, recipe_data)
  if recipe is None:
    return 2

  for c in recipe.components:
    if not c.clean(recipe.bld):
      return 3

  return 0
