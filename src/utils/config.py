import yaml

_CONFIG = {}

def load_config():
    global _CONFIG
    # 用户配置
    with open("config.yaml", "r", encoding="utf-8") as f:
        _CONFIG.update(yaml.safe_load(f))
    # 开发者配置
    with open("advance.yaml", "r", encoding="utf-8") as f:
        _CONFIG.update(yaml.safe_load(f))

def read_config(key: str):
    return _CONFIG[key]