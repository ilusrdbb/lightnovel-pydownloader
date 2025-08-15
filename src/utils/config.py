import textwrap
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
    # 更新配置
    _update_config()

def read_config(key: str):
    return _CONFIG_DATA[key]

def _update_config():
    if "esj_book_pwd" not in _CONFIG_DATA:
        _write_config(ADVANCE_CONFIG_FILE, textwrap.dedent("""
            
            # esj书籍密码配置 格式书籍id: 密码
            # 书籍id对应一本书的所有章节匹配优先级最高
            esj_book_pwd:
              114514: '1919810'
        """))
        _CONFIG_DATA["esj_book_pwd"] = {}

def _write_config(file_path, text):
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(text)
