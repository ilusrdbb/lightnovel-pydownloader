from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def get_app_root() -> Path:
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def get_resource_root() -> Path:
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS")).resolve()
    return get_app_root()


def get_config_path(filename: str) -> Path:
    return get_app_root() / filename


def get_resource_path(filename: str) -> Path:
    return get_resource_root() / filename


def get_log_dir() -> Path:
    return get_app_root() / "log"


def get_chrome_root() -> Path:
    return get_app_root() / "chrome"


def resolve_runtime_path(path_value: str) -> str:
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = get_app_root() / path
    return str(path.resolve(strict=False))
