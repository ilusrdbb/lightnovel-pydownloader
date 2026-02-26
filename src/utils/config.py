import os
import re
import sys
import shutil
from typing import Dict, Any, List, Tuple

import yaml

_CONFIG_DATA: Dict[str, Any] = {}

_MAIN_CONFIG_FILE = "config.yaml"
_ADVANCE_CONFIG_FILE = "advance.yaml"


def _get_bundled_path(filename: str) -> str:
    # 获取打包在exe中的资源文件路径
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, filename)
    # 非打包直接运行py的情况直接返回
    return filename


def load_config():
    global _CONFIG_DATA
    _CONFIG_DATA.clear()
    # 确保配置文件存在且完整
    _ensure_config_file(_MAIN_CONFIG_FILE)
    _ensure_config_file(_ADVANCE_CONFIG_FILE)
    # 一般配置
    with open(_MAIN_CONFIG_FILE, "r", encoding="utf-8") as f:
        _CONFIG_DATA.update(yaml.safe_load(f))
    # 高级配置
    with open(_ADVANCE_CONFIG_FILE, "r", encoding="utf-8") as f:
        _CONFIG_DATA.update(yaml.safe_load(f))


def read_config(key: str):
    return _CONFIG_DATA[key]


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
    with open(bundled_path, "r", encoding="utf-8") as f:
        default_content = f.read()
    if not os.path.exists(filename):
        # 文件不存在，直接复制默认配置
        shutil.copy2(bundled_path, filename)
        return
    # 文件存在，检查是否缺少配置项
    with open(filename, "r", encoding="utf-8") as f:
        content = f.read()
    existing_data = yaml.safe_load(content)
    if existing_data is None:
        # 文件为空或全是注释，覆盖写入默认配置
        shutil.copy2(bundled_path, filename)
        return
    # 找出缺失的key并追加
    default_blocks = _parse_key_blocks(default_content)
    missing_blocks = [block_text for key, block_text in default_blocks if key not in existing_data]
    if missing_blocks:
        with open(filename, "a", encoding="utf-8") as f:
            for block_text in missing_blocks:
                f.write(block_text)
