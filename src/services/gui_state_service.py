from __future__ import annotations

import shutil
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict

import yaml

from src.utils.paths import get_gui_state_path, get_resource_path

_STATE_RESOURCE = "resources/gui_state.yaml"


class GuiStateService:
    def __init__(self, path: Path | None = None):
        self.path = Path(path or get_gui_state_path())

    def get_site_login_state(self, site: str) -> Dict[str, Any]:
        state = self.load_state()
        sites = state.setdefault("sites", {})
        site_state = sites.setdefault(site, {})
        default_site_state = self._default_state()["sites"].get(site, {})
        merged = deepcopy(default_site_state)
        merged.update(site_state)
        return merged

    def save_site_login_state(
        self,
        site: str,
        remember_account: bool,
        remember_password: bool,
        password_storage: str = "",
        password_account: str = "",
    ):
        state = self.load_state()
        sites = state.setdefault("sites", {})
        sites[site] = {
            "remember_account": bool(remember_account),
            "remember_password": bool(remember_password),
            "password_storage": password_storage,
            "password_account": password_account,
        }
        self._dump_state(state)

    def load_state(self) -> Dict[str, Any]:
        self._ensure_state_file()
        with open(self.path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        merged = self._default_state()
        merged_sites = merged.setdefault("sites", {})
        for site, site_state in (data.get("sites") or {}).items():
            merged_sites.setdefault(site, {})
            merged_sites[site].update(site_state or {})
        return merged

    def _ensure_state_file(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            return
        template_path = Path(get_resource_path(_STATE_RESOURCE))
        shutil.copy2(template_path, self.path)

    def _dump_state(self, state: Dict[str, Any]):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            yaml.safe_dump(state, f, allow_unicode=True, sort_keys=False)

    def _default_state(self) -> Dict[str, Any]:
        return {
            "version": 1,
            "sites": {
                "esj": {
                    "remember_account": False,
                    "remember_password": False,
                    "password_storage": "",
                    "password_account": "",
                },
                "masiro": {
                    "remember_account": False,
                    "remember_password": False,
                    "password_storage": "",
                    "password_account": "",
                },
                "lk": {
                    "remember_account": False,
                    "remember_password": False,
                    "password_storage": "",
                    "password_account": "",
                },
                "yuri": {
                    "remember_account": False,
                    "remember_password": False,
                    "password_storage": "",
                    "password_account": "",
                },
            },
        }
