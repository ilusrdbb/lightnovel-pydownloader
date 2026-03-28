import os
import re
import shutil
from copy import deepcopy
from typing import Dict, Any, List, Tuple, Optional

import yaml

from src.utils.paths import get_config_path, get_resource_path, resolve_runtime_path

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
    for key in ("txt_dir", "epub_dir", "image_dir"):
        if key in runtime_config and runtime_config[key]:
            runtime_config[key] = resolve_runtime_path(str(runtime_config[key]))
    return runtime_config


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
