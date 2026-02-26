import re
import traceback

import execjs

from src.utils.log import log

# 初始JS字符串切片的偏移量
JS_SLICE_START = 31
JS_SLICE_END = -9
# 初始去混淆循环中涉及的关键字
KEYWORDS = ["window", "location", "'assign'", "'href'", "'replace'"]
# tempfunction变量的替换规则
NORMAL_REPLACEMENTS = [
    ("window.href", "somefunction"),
    ("location.assign", "tempfunction="),
    ("location.href", "tempfunction="),
    ("location.replace", "tempfunction="),
    ("location", "tempfunction="),
    ("tempfunction==", "tempfunction="),
]
# 关键字的替换规则
KEYWORD_REPLACEMENTS = [
    ("for", "forr"),
    ("do", "dodo"),
    ("in", "inin"),
    ("trining", "tring"),
]

def js_dsign(js: str) -> str:
    # 初始切片
    js = js[JS_SLICE_START:JS_SLICE_END]
    # 去混淆循环 替换被混淆的变量赋值
    for keyword_str in KEYWORDS:
        assignment_pattern = re.compile(r"(\b[_A-Za-z]\w*\b\s*=\s*%s\s*;)" % re.escape(keyword_str))
        match = assignment_pattern.search(js)
        if match:
            full_assignment = match.group(0)
            # 从匹配到的完整赋值语句中提取变量名
            var_name_match = re.match(r"(\b[_A-Za-z]\w*\b)\s*=", full_assignment)
            if not var_name_match:
                continue
            var_name = var_name_match.group(1).strip()
            # 移除原始的赋值语句
            js = js.replace(full_assignment, "", 1)
            # 将混淆的变量名替换为实际的关键字字符串
            js = re.sub(r'\b' + re.escape(var_name) + r'\b', keyword_str, js)
            # 将属性的方括号表示法转换为点表示法
            if keyword_str.startswith("'") and keyword_str.endswith("'"):
                prop_name = keyword_str.strip("'")
                # 处理单引号和双引号的方括号表示法，并转换为点表示法
                js = js.replace(f"['{prop_name}']", f".{prop_name}")
                js = js.replace(f'["{prop_name}"]', f".{prop_name}")
    # 特定的规范化替换
    for old, new in NORMAL_REPLACEMENTS:
        js = js.replace(old, new)
    # 关键字处理 特殊处理 if
    js = js.replace("if", "ifif")
    js = js.replace("ifif(name", "if(name")
    js = js.replace("ifif(caller", "if(caller")
    for old, new in KEYWORD_REPLACEMENTS:
        js = js.replace(old, new)
    return js

def get_dsign(js_code: str) -> str:
    processed_js = js_dsign(js_code)
    try:
        ctx = execjs.compile(processed_js)
        result = ctx.eval("tempfunction")
    except Exception as e:
        log.info(f"dsign解析失败 {str(e)}")
        log.debug(traceback.format_exc())
        return None
    # 在替换前确保输出是字符串
    if isinstance(result, str):
        result = result.replace("forrum", "forum")
    return str(result)