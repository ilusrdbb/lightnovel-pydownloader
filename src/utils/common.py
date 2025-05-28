import base64
import json
import os
import re
import traceback
import zlib
# 加载avif插件，不要删
import pillow_avif
from datetime import datetime
from os.path import basename
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse

from PIL import Image
from lxml import html

from src.models.book import Book
from src.utils.config import read_config
from src.utils.log import log


def get_xpath(text: str, site: str, name: str) -> Optional[List]:
    page_body = html.fromstring(text)
    return page_body.xpath(read_config("xpath_config")[site][name])

def get_html(text: str, site: str, name: str) -> str:
    if not text:
        return None
    page_body = html.fromstring(text)
    xpaths = page_body.xpath(read_config("xpath_config")[site][name])
    if not xpaths:
        return None
    return join([html.tostring(xpath, pretty_print=True, encoding="unicode") for xpath in xpaths], "\n")

def get_book_id(url: str, site: str) -> str:
    if site == "masiro":
        return url.split("?novel_id=")[-1]
    return re.search(r'\d+', url).group()

def handle_url_list(url_list: List[Any], site: str) -> Optional[List[str]]:
    if not list:
        return []
    return [get_book_id(str(url), site) for url in url_list]

def first(in_list: List[Any]) -> Optional[Any]:
    return None if not in_list else in_list[0]

def join(in_list: List[Any], concat=",") -> str:
    return None if not in_list else concat.join(in_list)

def find(in_list: List[Any], attr_name: str, attr_value: Any) -> Optional[Any]:
    if not in_list or not attr_name:
        return None
    for obj in in_list:
        if getattr(obj, attr_name, None) == attr_value:
            return obj
    return None

def filename_from_url(url: str) -> str:
    return basename(urlparse(url).path) if url else None

def unzip(text: str) -> Dict:
    return json.loads(zlib.decompress(base64.b64decode(text)).decode()) if text else None

def get_timestamp(time_str: str) -> int:
    time_format = "%Y-%m-%d %H:%M:%S"
    return int(datetime.strptime(time_str, time_format).timestamp())

def handle_avif(in_path: str) -> str:
    try:
        avif_image = Image.open(in_path)
        png_image = avif_image.convert('RGB')
        out_path = os.path.splitext(in_path)[0] + '.png'
        png_image.save(out_path, 'PNG')
        avif_image.close()
        png_image.close()
    except Exception as e:
        log.debug(f"avif转换失败 {str(e)} 路径{in_path}")
        log.debug(traceback.print_exc())
        return in_path
    # 删除源avif图片
    os.remove(in_path)
    return out_path

def handle_title(book: Book):
    if not book.book_name:
        return
    # windows 文件名限制
    char_map = {
        '/': ' ',
        '<': '《',
        '>': '》',
        ':': '：',
        '\\': ' ',
        '|': ' ',
        '?': '？',
        '*': ' '
    }
    # 替换不合法字符
    for char, replacement in char_map.items():
        book.book_name = book.book_name.replace(char, replacement)
    # linux 85 windows 127
    if len(book.book_name) > 85:
        book.book_name = book.book_name[:80] + '...'

def bbcode_to_html(text: str, lk_res: Dict[str, str], pic_datas: List[Dict[str, str]]) -> str:
    text = lk_bbcode_handler(text, lk_res, pic_datas)
    # 换行符处理
    text = text.replace("\n", "<br>")
    # 移除全部bbcode
    text = [re.sub(r"\[.*?\]", "", text)][0]
    return text

def lk_bbcode_handler(text: str, lk_res: Dict[str, str], pic_datas: List[Dict[str, str]]) -> str:
    # 文本中剔除插图
    result = text
    # bbcode img 轻国较旧的小说使用的图床
    img_list = re.findall(r"\[img\](.*?)\[/img\]", result)
    if img_list:
        for img_url in img_list:
            if img_url.startswith("http"):
                result = result.replace("[img]" + img_url + "[/img]", "<img src=\"" + img_url + "\">")
                pic_datas.append({"id": "", "url": img_url})
    # bbcode res 轻国较新的小说使用的图床
    if lk_res and lk_res.get("res") and lk_res["res"]["res_info"]:
        for key, value in lk_res["res"]["res_info"].items():
            result = result.replace("[res]" + key + "[/res]", "<img src=\"" + key + "\">")
            pic_datas.append({"id": key, "url": value["url"]})
    # bbcode attach 轻国较旧的小说引用图片类型的附件
    if lk_res and lk_res.get("attaches") and lk_res["attaches"]["res_info"]:
        for key, value in lk_res["attaches"]["res_info"].items():
            if value.get("isimage") == 1:
                result = result.replace("[attach]" + key + "[/attach]", "<img src=\"" + key + "\">")
                pic_datas.append({"id": key, "url": value["url"]})
    # 移除不符合的图片类型bbcode
    result = re.sub(r"\[res\].*?\[/res\]", "", result)
    result = re.sub(r"\[attach\].*?\[/attach\]", "", result)
    result = re.sub(r"\[img\].*?\[/img\]", "", result)
    return result