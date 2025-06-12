import os
import traceback
from typing import List

from ebooklib import epub
from ebooklib.epub import EpubBook
from zhconv import zhconv

from src.epub.calibre import push_calibre
from src.models.book import Book
from src.models.chapter import Chapter
from src.models.pic import Pic
from src.utils import common
from src.epub import css
from src.utils.config import read_config
from src.utils.log import log


def build_epub(book: Book):
    chapters = book.chapters
    if not chapters:
        return
    log.info(f"{book.book_name} 开始生成epub...")
    # 处理标题
    common.handle_title(book)
    epub_book = epub.EpubBook()
    # 元数据
    build_epub_metadata(epub_book, book)
    epub_chapters = []
    # 移除网站id相同的章节
    unique_chapters = []
    chapter_id_set = set()
    for chapter in chapters:
        if chapter.chapter_id not in chapter_id_set:
            unique_chapters.append(chapter)
            chapter_id_set.add(chapter.chapter_id)
    for chapter in unique_chapters:
        if not chapter.content:
            continue
        # 跳过打钱失败的章节
        if chapter.purchase_fail_flag and chapter.purchase_fail_flag == 1:
            continue
        # 图片处理
        pics = chapter.pics
        # 跳过字数过少的章节
        if not pics and read_config("least_words") > 0 and read_config("least_words") > len(chapter.content):
            continue
        replace_pics(chapter, pics, epub_book)
        epub_chapter = epub.EpubHtml(title=chapter.chapter_name, file_name=f"{chapter.chapter_id}.xhtml", lang="cn")
        # 繁转简
        content = zhconv.convert(chapter.content, "zh-hans") if read_config("convert_hans") else chapter.content
        # 字体反爬处理
        css.build_epub_css(content, epub_book, epub_chapter)
        # 标准html
        epub_chapter.content = f"<html><body>{content}</body></html>"
        epub_chapters.append(epub_chapter)
        epub_book.add_item(epub_chapter)
    # 目录和书脊
    epub_book.toc = epub_chapters
    epub_book.spine = epub_chapters
    epub_book.add_item(epub.EpubNcx())
    epub_book.add_item(epub.EpubNav())
    # 保存
    try:
        path = f"{read_config('epub_dir')}/{book.source}/{book.book_name}.epub"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        epub.write_epub(path, epub_book)
        log.info(f"{book.book_name} epub导出成功!")
    except Exception as e:
        log.info(f"{book.book_name} epub导出失败! {str(e)}")
        log.debug(traceback.print_exc())
        return
    # calibre-web
    if read_config("push_calibre")["enabled"]:
        push_calibre(book)

def build_epub_metadata(epub_book, book):
    # 元数据
    epub_book.set_identifier(book.id)
    epub_book.set_title(book.book_name)
    epub_book.set_language("zh")
    epub_book.add_author(book.author)
    if read_config("convert_hans") and book.describe:
        book.describe = zhconv.convert(book.describe, "zh-hans")
    epub_book.add_metadata("DC", "description", book.describe)
    epub_book.add_metadata("DC", "source", handle_source(book.source))
    epub_book.add_metadata("DC", "publisher", book.source)
    epub_book.add_metadata("DC", "rights",
                           "本电子书由lightnovel-pydownloader制作生成，仅供个人使用，不得对外传播以及用于商业用途。")
    if book.tags:
        for tag in book.tags.split(","):
            epub_book.add_metadata("DC", "subject", tag)
    cover_dir = f"{read_config('image_dir')}/{book.source}/{book.book_id}"
    if book.cover_url and os.path.isdir(cover_dir):
        for file_name in os.listdir(cover_dir):
            file_path = os.path.join(cover_dir, file_name)
            if os.path.isfile(file_path):
                epub_book.set_cover(file_name, open(file_path, 'rb').read())
                break

def handle_source(code: str):
    if code == "masiro":
        return "真白萌"
    if code == "lk":
        return "轻之国度"
    if code == "yuri":
        return "百合会"
    return code

def replace_pics(chapter: Chapter, pics: List[Pic], epub_book: EpubBook):
    if not pics:
        return
    content = chapter.content
    for pic in pics:
        if not pic.pic_path:
            continue
        try:
            image_data = open(pic.pic_path, "rb").read()
            image_name = common.filename_from_url(pic.pic_path)
            image_type = image_name.split(".")[-1]
            image = epub.EpubImage(uid=image_name, file_name="Image/" + image_name,
                                   media_type="image/" + image_type, content=image_data)
            epub_book.add_item(image)
            if pic.pic_id:
                # 轻国特殊处理
                content = content.replace(pic.pic_id, f"Image/{image_name}")
            else:
                content = content.replace(pic.pic_url, f"Image/{image_name}")
        except Exception as e:
            log.debug(f"{pic.pic_path} 替换图片失败 {str(e)}")
            log.debug(traceback.print_exc())
    # 百合会特殊处理
    if "static/image/common/none.gif" in content and 'file="Image/' in content:
        content = content.replace("src=\"static/image/common/none.gif\"", "")
        content = content.replace('file="Image/', 'src="Image/')
    chapter.content = content
