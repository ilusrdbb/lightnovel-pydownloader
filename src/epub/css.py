import re
import traceback

import requests
from ebooklib import epub
from ebooklib.epub import EpubBook, EpubHtml

from src.utils import common
from src.utils.log import log


def get_font_url(text: str) -> str:
    try:
        # 提取css的地址
        css_pattern = r'https?://[^\s"\']+\.css'
        css_url = common.first(re.findall(css_pattern, text))
        if not css_url:
            return None
        # 提取字体地址
        res = requests.get(css_url)
        res.raise_for_status()
        css_text = res.text
        if "format('woff')" not in css_text:
            return None
        font_pattern = r"(https?://[^\s')]+\.woff)"
        return common.first(re.findall(font_pattern, css_text))
    except Exception as e:
        log.info(f"提取字体地址失败: {e}")
        log.debug(traceback.print_exc())
        return None


def build_epub_css(text: str, epub_book: EpubBook, epub_chapter: EpubHtml):
    # 获取字体地址
    font_url = get_font_url(text)
    if not font_url:
        return
    log.debug(font_url)
    # 下载
    try:
        res = requests.get(font_url)
        res.raise_for_status()
        file_name = common.filename_from_url(font_url)
        font_name = file_name.replace('.woff', '')
        font_item = epub.EpubItem(
            uid=f"font_{font_name}",
            file_name=f"fonts/{file_name}",
            media_type='application/font-woff',
            content=res.content
        )
        # 将字体文件添加到书中
        epub_book.add_item(font_item)
        # 自定义css
        css_content = f"""
        @font-face {{
            font-family: '{font_name}';
            src: url(../fonts/{file_name}) format('woff');
            font-weight: normal;
            font-style: normal;
            font-display: swap;
        }}

        body {{
            font-family: '{font_name}'
        }}
        """
        css_item = epub.EpubItem(
            uid="style_main",
            file_name=f"style/{font_name}.css",
            media_type="text/css",
            content=css_content.encode('utf-8')
        )
        # 将css文件添加到书中
        epub_book.add_item(css_item)
        # 将css文件链接到章节中
        epub_chapter.add_item(css_item)
    except Exception as e:
        log.info(f"css解析失败: {e}")
        log.debug(traceback.print_exc())