import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import bip.cli as cli
import bip.component as component
import bip.lang as lang
import bip.lang.c as C
import bip.plat as plat
import bip.version as version


@dataclass
class Recipe:
    path: Path
    components: list[component.Component]
    lang_config: lang.MultiConfig

    @classmethod
    def load(cls, path: Path, info: component.abc.RunInfo) -> Optional["Recipe"]:
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

        if "bip" in build:
            raw_reqr = build.pop("bip")
            reqr = version.parse_reqr(raw_reqr)
            if reqr is None:
                cli.warn(f"Could not parse version requirement: {raw_reqr}")
            else:
                # print(reqr)
                if not reqr.is_satisfied():
                    cli.error(
                        f"This recipe is meant for bip {raw_reqr}",
                        f"You are currently using bip {version.VERSION_STR}",
                    )
                    return None

        base_paths = component.Paths.from_dict(build, info)

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
