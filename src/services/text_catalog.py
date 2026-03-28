from __future__ import annotations

import shutil
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from src.utils.paths import get_gui_text_override_path, get_resource_path

_DEFAULT_TEXT_RESOURCE = "resources/gui_texts.yaml"
_OVERRIDE_TEMPLATE_RESOURCE = "resources/gui_text_overrides.example.yaml"


class TextCatalog:
    def __init__(
        self,
        default_path: Optional[Path] = None,
        override_path: Optional[Path] = None,
    ):
        self.default_path = Path(default_path or get_resource_path(_DEFAULT_TEXT_RESOURCE))
        self.override_path = Path(override_path or get_gui_text_override_path())
        self._cache: Optional[Dict[str, Any]] = None

    def get_text(self, key: str, default: Optional[str] = None, **kwargs: Any) -> str:
        value = self._lookup(key)
        if value is None:
            value = default if default is not None else key
        if not isinstance(value, str):
            value = str(value)
        if kwargs:
            try:
                return value.format(**kwargs)
            except Exception:
                return value
        return value

    def reload(self):
        self._cache = None

    def _lookup(self, key: str) -> Any:
        data = self._load_catalog()
        current: Any = data
        for part in key.split("."):
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
        return current

    def _load_catalog(self) -> Dict[str, Any]:
        if self._cache is not None:
            return self._cache
        self._ensure_override_file()
        with open(self.default_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        merged = deepcopy(data)
        with open(self.override_path, "r", encoding="utf-8") as f:
            override_data = yaml.safe_load(f) or {}
        self._deep_merge(merged, override_data)
        self._cache = merged
        return merged

    def _ensure_override_file(self):
        self.override_path.parent.mkdir(parents=True, exist_ok=True)
        if self.override_path.exists():
            return
        template_path = Path(get_resource_path(_OVERRIDE_TEMPLATE_RESOURCE))
        shutil.copy2(template_path, self.override_path)

    def _deep_merge(self, target: Dict[str, Any], source: Dict[str, Any]):
        for key, value in source.items():
            if isinstance(value, dict) and isinstance(target.get(key), dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = value


_CATALOG: Optional[TextCatalog] = None


def get_text_catalog() -> TextCatalog:
    global _CATALOG
    if _CATALOG is None:
        _CATALOG = TextCatalog()
    return _CATALOG
