import os

from lxml import html
from zhconv import zhconv

from src.models.book import Book
from src.utils import common
from src.utils.config import read_config
from src.utils.log import log


def build_txt(book: Book):
    chapters = book.chapters
    if not chapters:
        return
    log.info(f"{book.book_name} 开始生成txt...")
    common.handle_title(book)
    txt_content = ""
    for chapter in chapters:
        if not chapter.content:
            continue
        # 跳过打钱失败的章节
        if chapter.purchase_fail_flag and chapter.purchase_fail_flag == 1:
            continue
        # 跳过字数过少的章节
        if read_config("least_words") > 0 and read_config("least_words") > len(chapter.content):
            continue
        # 繁转简
        chapter_content = zhconv.convert(chapter.content, 'zh-hans') if read_config('convert_hans') else chapter.content
        # html转纯文字
        page_body = html.fromstring(chapter_content)
        raw_list = page_body.xpath("//text()")
        temp_list = (s.replace("\n", "") for s in raw_list)
        content_list = [s for s in temp_list if s]
        txt_content += chapter.chapter_name + "\n\n"
        txt_content += "\n".join(content_list) + "\n\n"
    # 保存
    path = f"{read_config('txt_dir')}/{book.source}/{book.book_name}.txt"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(txt_content)
    log.info(f"{book.book_name} txt导出成功!")