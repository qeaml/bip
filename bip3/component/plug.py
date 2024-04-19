"""
PlugComponent
"""

import importlib
from types import ModuleType
from typing import Callable, Optional

from .abc import *


class PlugComponent(Component):
    _module: Optional[ModuleType]
    _settings: dict
    _base_paths: Paths

    # the two required functions
    ConfigureFn = Callable[[dict[str, str]], bool]
    WantRunFn = Callable[[], bool]
    # the optional functions
    RunFn = Callable[[], bool]
    CleanFn = Callable[[], None]

    _configure: ConfigureFn
    _run: RunFn
    _want_run: Optional[WantRunFn]
    _clean: Optional[CleanFn]

    def __init__(
        self,
        name: str,
        src_name: str,
        platcond: Optional[plat.ID],
        settings: dict,
        base_paths: Paths,
    ):
        super(PlugComponent, self).__init__(name, src_name, platcond)
        self._module = None
        self._settings = settings
        self._base_paths = base_paths

        self._want_run = None
        self._clean = None

    @classmethod
    def from_dict(
        cls,
        raw: dict,
        name: str,
        src_name: str,
        platform: Optional[plat.ID],
        base_paths: Paths,
    ) -> Optional[Component]:
        return cls(name, src_name, platform, raw, base_paths)

    def _ensure_module(self) -> bool:
        if self._module is not None:
            return True

        mod_path = self._base_paths.src.joinpath(self.out_name, "plug.py")
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
            err(f"{mod_path} does not define configure(dict)")
            return False

        if not hasattr(module, "run"):
            err(f"{mod_path} does not define run()")
            return False

        if not module.configure(self._settings):
            return False

        self._module = module
        self._configure = self._module.configure
        self._run = self._module.run

        if hasattr(self._module, "want_run"):
            self._want_run = self._module.want_run

        if hasattr(self._module, "clean"):
            self._clean = self._module.clean

        return True

    def want_run(self) -> bool:
        if not self._ensure_module():
            return False
        if self._want_run is not None:
            return self._want_run()
        return True

    def run(self, info: RunInfo) -> bool:
        if not self._ensure_module():
            return False
        return self._run()

    def clean(self) -> bool:
        if not self._ensure_module():
            return False
        if self._clean is not None:
            return self._clean()
        return True

    def contrib(self) -> list[Contrib]:
        return []
