import os
import re
import shutil
from copy import deepcopy
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

import yaml

from src.utils.paths import (
    get_config_path,
    get_data_root,
    get_default_output_root,
    get_resource_path,
    is_macos_app,
    resolve_runtime_path,
)

_CONFIG_DATA: Dict[str, Any] = {}

_MAIN_CONFIG_FILE = "config.yaml"
_ADVANCE_CONFIG_FILE = "advance.yaml"


def _get_bundled_path(filename: str) -> str:
    return str(get_resource_path(filename))


def get_config_file_path(filename: str) -> str:
    return str(get_config_path(filename))


def load_config(config_data: Optional[Dict[str, Any]] = None):
    global _CONFIG_DATA
    _CONFIG_DATA.clear()
    if config_data is None:
        config_data = load_config_files()
    _CONFIG_DATA.update(normalize_config_data(config_data))


def read_config(key: str):
    return _CONFIG_DATA[key]


def get_loaded_config() -> Dict[str, Any]:
    return deepcopy(_CONFIG_DATA)


def load_config_files() -> Dict[str, Any]:
    _ensure_config_file(_MAIN_CONFIG_FILE)
    _ensure_config_file(_ADVANCE_CONFIG_FILE)
    merged_data: Dict[str, Any] = {}
    with open(get_config_file_path(_MAIN_CONFIG_FILE), "r", encoding="utf-8") as f:
        merged_data.update(yaml.safe_load(f) or {})
    with open(get_config_file_path(_ADVANCE_CONFIG_FILE), "r", encoding="utf-8") as f:
        merged_data.update(yaml.safe_load(f) or {})
    return merged_data


def normalize_config_data(config_data: Dict[str, Any]) -> Dict[str, Any]:
    runtime_config = deepcopy(config_data)
    output_root = runtime_config.get("output_root")
    if output_root:
        normalized_output_root = resolve_runtime_path(str(output_root))
        runtime_config["output_root"] = normalized_output_root
        runtime_config["epub_dir"] = str(Path(normalized_output_root) / "epub")
        runtime_config["txt_dir"] = str(Path(normalized_output_root) / "txt")
        runtime_config["image_dir"] = str(Path(normalized_output_root) / "images")
    else:
        for key in ("txt_dir", "epub_dir", "image_dir"):
            if key in runtime_config and runtime_config[key]:
                runtime_config[key] = resolve_runtime_path(str(runtime_config[key]))
        inferred_output_root = _infer_output_root(runtime_config)
        if inferred_output_root:
            runtime_config["output_root"] = inferred_output_root
        elif is_macos_app():
            default_output_root = str(get_default_output_root())
            runtime_config["output_root"] = default_output_root
            runtime_config["epub_dir"] = str(Path(default_output_root) / "epub")
            runtime_config["txt_dir"] = str(Path(default_output_root) / "txt")
            runtime_config["image_dir"] = str(Path(default_output_root) / "images")
        else:
            runtime_config["output_root"] = str(get_default_output_root())
    chrome_path = runtime_config.get("chrome_path")
    runtime_config["chrome_path"] = (
        resolve_runtime_path(str(chrome_path)) if chrome_path else ""
    )
    update_strategy = str(runtime_config.get("update_strategy", "") or "").strip()
    if update_strategy not in {"only_new", "refresh_changed", "full_refetch"}:
        runtime_config["update_strategy"] = "only_new"
    else:
        runtime_config["update_strategy"] = update_strategy
    _apply_secure_login_credentials(runtime_config)
    return runtime_config


def _infer_output_root(config_data: Dict[str, Any]) -> str:
    epub_dir = config_data.get("epub_dir")
    txt_dir = config_data.get("txt_dir")
    image_dir = config_data.get("image_dir")
    if not epub_dir or not txt_dir or not image_dir:
        return ""
    epub_path = Path(str(epub_dir))
    txt_path = Path(str(txt_dir))
    image_path = Path(str(image_dir))
    candidate_root = epub_path.parent
    if txt_path == candidate_root / "txt" and image_path == candidate_root / "images" and epub_path == candidate_root / "epub":
        return str(candidate_root)
    return ""


def _parse_key_blocks(text: str) -> List[Tuple[str, str]]:
    # 将yaml文本按key拆分 包含该key上方紧邻的注释行
    lines = text.splitlines(keepends=True)
    blocks: List[Tuple[str, str]] = []
    comment_buf: list = []
    key_pattern = re.compile(r'^([a-zA-Z_]\w*)\s*:')
    for line in lines:
        m = key_pattern.match(line)
        if m:
            key_name = m.group(1)
            block_lines = comment_buf + [line]
            comment_buf = []
            blocks.append((key_name, block_lines))
        elif blocks and (line.startswith(' ') or line.startswith('\t')):
            blocks[-1][1].append(line)
        else:
            comment_buf.append(line)
    return [(key, ''.join(block_lines)) for key, block_lines in blocks]


def _ensure_config_file(filename: str):
    # 确保配置文件存在且包含所有必要的配置项
    bundled_path = _get_bundled_path(os.path.basename(filename))
    config_path = get_config_file_path(filename)
    if not os.path.exists(bundled_path):
        raise FileNotFoundError(f"默认配置文件不存在: {bundled_path}")
    Path(get_data_root()).mkdir(parents=True, exist_ok=True)
    with open(bundled_path, "r", encoding="utf-8") as f:
        default_content = f.read()
    if not os.path.exists(config_path):
        # 文件不存在，直接复制默认配置
        shutil.copy2(bundled_path, config_path)
        return
    # 文件存在，检查是否缺少配置项
    with open(config_path, "r", encoding="utf-8") as f:
        content = f.read()
    existing_data = yaml.safe_load(content)
    if existing_data is None:
        # 文件为空或全是注释，覆盖写入默认配置
        shutil.copy2(bundled_path, config_path)
        return
    # 找出缺失的key并追加
    default_blocks = _parse_key_blocks(default_content)
    missing_blocks = [block_text for key, block_text in default_blocks if key not in existing_data]
    if missing_blocks:
        with open(config_path, "a", encoding="utf-8") as f:
            for block_text in missing_blocks:
                f.write(block_text)


def _apply_secure_login_credentials(runtime_config: Dict[str, Any]):
    login_info = runtime_config.get("login_info")
    if not isinstance(login_info, dict):
        return
    try:
        from src.services.gui_state_service import GuiStateService
        from src.services.keychain_store import KeychainStore
    except Exception:
        return

    store = KeychainStore()
    if not store.is_available():
        return

    state_service = GuiStateService()
    for site, site_login in login_info.items():
        if not isinstance(site_login, dict):
            continue
        site_state = state_service.get_site_login_state(str(site))
        if not site_state.get("remember_password"):
            continue
        account = str(site_state.get("password_account") or site_login.get("username") or "").strip()
        if not account or site_login.get("password"):
            continue
        password = store.load_password(str(site), account)
        if password:
            site_login["password"] = password
