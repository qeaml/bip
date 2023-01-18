from pathlib import Path
from .recipe import Recipe
import tomllib
import bip.common as common

def build(root: Path, log: common.Log) -> int:
  recipe_file = root.joinpath("recipe.toml")
  if not recipe_file.exists():
    print("Not a valid project. No recipe file was found.")
    return 1

  recipe_data = {}
  with recipe_file.open("rb") as f:
    recipe_data = tomllib.load(f)

  recipe = Recipe.from_dict(log, root, recipe_data)
  if recipe is None:
    return 2

  if not recipe.build():
    return 3

  return 0
