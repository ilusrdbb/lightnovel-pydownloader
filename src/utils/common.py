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
from typing import List, Optional, Dict
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
    if site == "esj":
        return re.search(r"\d+", url).group()
    if site == "masiro":
        return url.split("?novel_id=")[-1]
    return re.search(r'\d+', url).group()

def handle_url_list(url_list: List, site: str) -> Optional[List[str]]:
    if not list:
        return []
    return [get_book_id(str(url), site) for url in url_list]

def first(in_list: List):
    return None if not in_list else in_list[0]

def join(in_list: List, concat=",") -> str:
    return None if not in_list else concat.join(in_list)

def find(in_list: List, attr_name: str, attr_value):
    if not in_list or not attr_name:
        return None
    for obj in in_list:
        if getattr(obj, attr_name, None) == attr_value:
            return obj
    return None

def filename_from_url(url: str) -> str:
    return basename(urlparse(url).path) if url else None

def unzip(text: str) -> Dict:
    return json.loads(zlib.decompress(base64.b64decode(text)).decode())

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