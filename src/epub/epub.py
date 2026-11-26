import os
import traceback
from html import escape
from typing import List

from ebooklib import epub
from ebooklib.epub import EpubBook
from zhconv import zhconv
from lxml import html

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
    if book.source == "lk2" and read_config("lk_export_column") and not book.column_export_flag:
        # 按卷分组
        column_map: dict[str, list[Chapter]] = {}
        for chapter in chapters:
            if not chapter.lk_column_name:
                continue
            column_map.setdefault(chapter.lk_column_name, []).append(chapter)
        if not column_map:
            log.info(f"{book.book_name} 空卷未导出epub")
            return
        for lk_column_name, column_chapter_list in column_map.items():
            # 按照卷构造book
            column_book = Book()
            column_book.chapters = column_chapter_list
            column_book.cache_book_name = book.book_name
            column_book.book_name = lk_column_name
            column_book.source = book.source
            column_book.id = book.id
            column_book.book_id = book.book_id
            column_book.author = book.author
            column_book.describe = book.describe
            column_book.tags = book.tags
            column_book.cover_url = book.cover_url
            column_book.column_export_flag = True
            build_epub(column_book)
        return
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
        epub_chapter.content = f"<html><body>{safe_content(content)}</body></html>"
        epub_chapters.append(epub_chapter)
        epub_book.add_item(epub_chapter)
    if not epub_chapters:
        log.info(f"{book.book_name} 空章节未导出epub")
        return
    # 目录和书脊
    epub_book.toc = epub_chapters
    epub_book.spine = epub_chapters
    epub_book.add_item(epub.EpubNcx())
    epub_book.add_item(epub.EpubNav())
    # 保存
    try:
        if read_config("lk_export_column"):
            path = f"{read_config('epub_dir')}/{book.source}/{common.safe_filename(book.cache_book_name)}/{common.safe_filename(book.book_name)}.epub"
        else:
            path = f"{read_config('epub_dir')}/{book.source}/{common.safe_filename(book.book_name)}.epub"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        epub.write_epub(path, epub_book)
        log.info(f"{book.book_name} epub导出成功!")
    except Exception as e:
        log.info(f"{book.book_name} epub导出失败! {str(e)}")
        log.debug(traceback.format_exc())
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
                with open(file_path, 'rb') as f:
                    epub_book.set_cover(file_name, f.read())
                break

def handle_source(code: str) -> str:
    if code == "masiro":
        return "真白萌"
    if code == "lk" or code == "lk2":
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
            with open(pic.pic_path, "rb") as f:
                image_data = f.read()
            image_name = common.filename_from_url(pic.pic_path)
            image_type = image_name.split(".")[-1]
            image = epub.EpubImage(uid=image_name, file_name=f"Image/{chapter.chapter_id}/{image_name}",
                                   media_type=f"image/{image_type}", content=image_data)
            epub_book.add_item(image)
            image_src = f"Image/{chapter.chapter_id}/{image_name}"
            if pic.pic_id:
                # 旧轻国特殊处理
                content = content.replace(pic.pic_id, image_src)
            else:
                escaped_url = escape(pic.pic_url, quote=False)
                if escaped_url != pic.pic_url:
                    content = content.replace(escaped_url, image_src)
                content = content.replace(pic.pic_url, image_src)
        except Exception as e:
            log.debug(f"{pic.pic_path} 替换图片失败 {str(e)}")
            log.debug(traceback.format_exc())
    # 百合会特殊处理
    if "static/image/common/none.gif" in content and 'file="Image/' in content:
        content = content.replace("src=\"static/image/common/none.gif\"", "")
        content = content.replace('file="Image/', 'src="Image/')
    chapter.content = content

def safe_content(content: str) -> str:
    if not content or "<" not in content:
        return content
    # 安全方面考量 导出前清洗html
    try:
        root = html.fromstring(content)
    except Exception as e:
        log.debug(traceback.format_exc())
        return content
    for link in root.xpath("//link"):
        href = link.attrib.get("href", "")
        if href.lower().startswith("data:text/css"):
            # 规避字体反爬的处理
            continue
        link.getparent().remove(link)
    for tag in root.xpath("//script | //iframe | //object | //embed"):
        tag.getparent().remove(tag)
    for el in root.xpath("//*[@*]") + [root]:
        for attr in [a for a in el.attrib if a.lower().startswith("on")]:
            del el.attrib[attr]
        for attr in ("href", "src", "xlink:href"):
            val = el.attrib.get(attr, "")
            if val.lower().startswith(("javascript:", "data:text/html")):
                del el.attrib[attr]
    return html.tostring(root, encoding="unicode")

