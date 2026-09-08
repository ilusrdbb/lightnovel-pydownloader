import os
import re
import traceback
# 加载avif插件，不要删
import pillow_avif
from datetime import datetime
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse

from PIL import Image
from lxml import html

from src.core.constants import CHAR_MAP, NAME_TRIM_THRESHOLD, NAME_TRIM_LENGTH
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
        return url.split("?novel_id=")[-1] if "?novel_id=" in url else url
    if site == "yuri":
        return url.split("-")[1] if "-" in url else url
    return re.search(r'\d+', url).group()

def handle_url_list(url_list: List[Any], site: str) -> Optional[List[str]]:
    if not url_list:
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
    path = urlparse(url).path
    filename = os.path.basename(path)
    # 一部分cdn带@的特殊处理
    return filename.split('@')[0]

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
        log.debug(traceback.format_exc())
        return in_path
    # 删除源avif图片
    os.remove(in_path)
    return out_path

def handle_title(book: Book):
    if not book.book_name:
        return
    for char, replacement in CHAR_MAP.items():
        book.book_name = book.book_name.replace(char, replacement)
    if len(book.book_name) > NAME_TRIM_THRESHOLD:
        book.book_name = book.book_name[:NAME_TRIM_LENGTH] + "..."

def safe_filename(name: str) -> str:
    for char, replacement in CHAR_MAP.items():
        name = name.replace(char, replacement)
    return name.strip(" .")