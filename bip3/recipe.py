import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cli
import component
import lang
import lang.c as C
import plat


@dataclass
class Recipe:
    path: Path
    components: list[component.Component]
    lang_config: lang.MultiConfig

    @classmethod
    def load(cls, path: Path) -> Optional["Recipe"]:
        raw: dict[str, Any]
        try:
            with path.open("rb") as f:
                raw = tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            cli.error(f"Invalid recipe file: {e}")
            return None

        if "build" not in raw:
            cli.error("Recipe file must define [build]")
            return None

        build = raw.pop("build")
        base_paths = component.Paths.from_dict(build)

        c_config = C.Config()
        if "c" in build:
            raw_config = build.pop("c")
            c_config.load_overrides(raw_config)
        cpp_config = C.Config()
        if "cpp" in build:
            raw_config = build.pop("cpp")
            cpp_config.load_overrides(raw_config)
        lang_config = lang.MultiConfig(c_config, cpp_config)

        components = []
        for cmpnt_name, raw_cmpnt in raw.items():
            cmpnt = component.from_dict(raw_cmpnt, cmpnt_name, base_paths, lang_config)
            if cmpnt is None:
                return None
            if cmpnt.platform is not None:
                if cmpnt.platform != plat.native():
                    continue
            components.append(cmpnt)

        return cls(path, components, lang_config)
