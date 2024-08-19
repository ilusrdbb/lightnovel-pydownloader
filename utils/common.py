import base64
import json
import re
import zlib
from datetime import datetime
from os.path import basename
from urllib.parse import urlparse

from models.book import Book


def first(in_list: list):
    if not in_list:
        return None
    return in_list[0]


def join(in_list: list, concat=",") -> str:
    if not in_list:
        return None
    return concat.join(in_list)


def find(in_list: list, attr_name: str, attr_value):
    if not in_list or not attr_name:
        return None
    for obj in in_list:
        if getattr(obj, attr_name, None) == attr_value:
            return obj
    return None


def find_list(in_list: list, attr_name: str, attr_value) -> list:
    if not in_list or not attr_name:
        return None
    result_list = []
    for obj in in_list:
        if getattr(obj, attr_name, None) == attr_value:
            result_list.append(obj)
    return result_list


def copy(source, target):
    if not source or not target:
        return
    for key, value in vars(source).items():
        setattr(target, key, value)


def filename_from_url(url: str):
    if not url:
        return None
    path = urlparse(url).path
    return basename(path)


def unzip(text: str):
    b = base64.b64decode(text)
    s = zlib.decompress(b).decode()
    return json.loads(s)


def time(time_str: str) -> int:
    time_format = "%Y-%m-%d %H:%M:%S"
    time_object = datetime.strptime(time_str, time_format)
    return int(time_object.timestamp())


def bbcode_to_html(text: str, lk_res: dict, pic_urls: list) -> str:
    text = lk_bbcode_handler(text, lk_res, pic_urls)
    # 换行符处理
    text = text.replace("\n", "<br>")
    # 移除全部bbcode
    text = [re.sub(r"\[.*?\]", "", text)][0]
    return text


def lk_bbcode_handler(text: str, lk_res: dict, pic_urls: list) -> str:
    # 文本中剔除插图
    result = text
    # bbcode img 轻国较旧的小说使用的图床
    img_list = re.findall(r"\[img\](.*?)\[/img\]", result)
    if img_list:
        for img_url in img_list:
            if img_url.startswith("http"):
                result = result.replace("[img]" + img_url + "[/img]", "<img src=\"" + img_url + "\">")
                pic_urls.append({"id": "", "url": img_url})
    # bbcode res 轻国较新的小说使用的图床
    if lk_res and lk_res.get("res") and lk_res["res"]["res_info"]:
        for key, value in lk_res["res"]["res_info"].items():
            result = result.replace("[res]" + key + "[/res]", "<img src=\"" + key + "\">")
            pic_urls.append({"id": key, "url": value["url"]})
    # bbcode attach 轻国较旧的小说引用图片类型的附件
    if lk_res and lk_res.get("attaches") and lk_res["attaches"]["res_info"]:
        for key, value in lk_res["attaches"]["res_info"].items():
            if value.get("isimage") == 1:
                result = result.replace("[attach]" + key + "[/attach]", "<img src=\"" + key + "\">")
                pic_urls.append({"id": key, "url": value["url"]})
    # 移除不符合的图片类型bbcode
    result = re.sub(r"\[res\].*?\[/res\]", "", result)
    result = re.sub(r"\[attach\].*?\[/attach\]", "", result)
    result = re.sub(r"\[img\].*?\[/img\]", "", result)
    return result


def handle_title(book: Book):
    if not book.book_name:
        return
    # windows 文件名限制
    book.book_name = book.book_name.replace("/", " ")
    book.book_name = book.book_name.replace("<", "《")
    book.book_name = book.book_name.replace(">", "》")
    book.book_name = book.book_name.replace(":", "：")
    book.book_name = book.book_name.replace("\\", " ")
    book.book_name = book.book_name.replace("|", " ")
    book.book_name = book.book_name.replace("?", "？")
    book.book_name = book.book_name.replace("*", " ")
    # linux 85 windows 127
    if len(book.book_name) > 85:
        book.book_name = book.book_name[:85]
