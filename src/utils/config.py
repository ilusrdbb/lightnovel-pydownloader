from typing import Dict, Any

import yaml

_CONFIG_DATA: Dict[str, Any] = {}

MAIN_CONFIG_FILE = "config.yaml"
ADVANCE_CONFIG_FILE = "advance.yaml"

def load_config():
    global _CONFIG_DATA
    _CONFIG_DATA.clear()
    # 一般配置
    with open(MAIN_CONFIG_FILE, "r", encoding="utf-8") as f:
        _CONFIG_DATA.update(yaml.safe_load(f))
    # 高级配置
    with open(ADVANCE_CONFIG_FILE, "r", encoding="utf-8") as f:
        _CONFIG_DATA.update(yaml.safe_load(f))

def read_config(key: str):
    return _CONFIG_DATA[key]