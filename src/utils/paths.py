from __future__ import annotations

import sys
from pathlib import Path

_APP_DIR_NAME = "lightnovel-pydownloader"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def is_macos_app() -> bool:
    return is_frozen() and sys.platform == "darwin"


def get_app_root() -> Path:
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def get_resource_root() -> Path:
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS")).resolve()
    return get_app_root()


def get_data_root() -> Path:
    if is_macos_app():
        return Path.home() / "Library" / "Application Support" / _APP_DIR_NAME
    return get_app_root()


def get_user_data_root() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / _APP_DIR_NAME
    return get_data_root()


def get_default_output_root() -> Path:
    if is_macos_app():
        return Path.home() / "Documents" / _APP_DIR_NAME
    return get_app_root()


def get_config_path(filename: str) -> Path:
    return get_data_root() / filename


def get_resource_path(filename: str) -> Path:
    return get_resource_root() / filename


def get_log_dir() -> Path:
    return get_data_root() / "log"


def get_chrome_root() -> Path:
    return get_data_root() / "chrome"


def get_database_path() -> Path:
    return get_data_root() / "lightnovel.db"


def get_bookshelf_db_path() -> Path:
    return get_user_data_root() / "bookshelf.db"


def get_gui_state_path() -> Path:
    return get_user_data_root() / "gui_state.yaml"


def get_gui_text_override_path() -> Path:
    return get_user_data_root() / "gui_text_overrides.yaml"


def resolve_runtime_path(path_value: str) -> str:
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = get_data_root() / path
    return str(path.resolve(strict=False))
