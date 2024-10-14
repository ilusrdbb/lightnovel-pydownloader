import os
from typing import Optional

from ebooklib import epub
from lxml import html
from zhconv import zhconv

from models.book import Book
from models.chapter import Chapter
from sqlite.database import Database
from utils import image, config, log, common, push


def build_epub(book: Book, chapter_list: Optional[Chapter]):
    build_txt(book, chapter_list)
    if not chapter_list:
        return
    log.info(book.book_name + " 开始生成epub...")
    common.handle_title(book)
    path = config.read("epub_dir") + "/" + book.source + "/" + book.book_name + ".epub"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    epub_book = epub.EpubBook()
    # 元数据
    epub_book.set_identifier(book.id)
    epub_book.set_title(book.book_name)
    epub_book.set_language("zh")
    epub_book.add_author(book.author)
    if config.read('convert_hans') and book.describe:
        book.describe = zhconv.convert(book.describe, 'zh-hans')
    epub_book.add_metadata("DC", "description", book.describe)
    epub_book.add_metadata("DC", "source", book.source)
    epub_book.add_metadata("DC", "publisher", book.source)
    epub_book.add_metadata("DC", "contributor", "lightnovel-pydownloader")
    epub_book.add_metadata("DC", "rights", "本电子书由lightnovel-pydownloader制作生成，仅供个人使用，不得对外传播以及用于商业用途。")
    if book.tags:
        for tag in book.tags.split(","):
            epub_book.add_metadata("DC", "subject", tag)
    if book.cover_url:
        cover_path = config.read("image_dir") + "/" + book.source + "/" + book.book_id + "/book_cover.jpg"
        try:
            epub_book.set_cover("cover.jpg", open(cover_path, 'rb').read())
        except:
            pass
    epub_chapters = []
    for chapter in chapter_list:
        # 跳过esj外链
        if chapter.chapter_id.startswith("http"):
            continue
        # 跳过打钱失败的章节
        if chapter.purchase_fail_flag and chapter.purchase_fail_flag == 1:
            continue
        # 图片替换
        with Database() as db:
            pics = db.pic.get_nonnull_list(chapter.id)
        # 跳过字数过少的章节
        if not pics and not chapter.content:
            continue
        if not pics and config.read("least_words") > 0 and config.read("least_words") > len(chapter.content):
            continue
        image.replace(chapter, pics, epub_book)
        epub_chapter = epub.EpubHtml(title=chapter.chapter_name, file_name=chapter.chapter_id + ".xhtml", lang="cn")
        # 繁转简
        content = chapter.content
        if config.read('convert_hans'):
            content = zhconv.convert(content, 'zh-hans')
        epub_chapter.content = content
        epub_chapters.append(epub_chapter)
        epub_book.add_item(epub_chapter)
    # 目录和书脊
    epub_book.toc = epub_chapters
    epub_book.spine = epub_chapters
    epub_book.add_item(epub.EpubNcx())
    epub_book.add_item(epub.EpubNav())
    # css
    style = "body { font-family: Times, Times New Roman, serif; }"
    nav_css = epub.EpubItem(uid="style_nav", file_name="style/nav.css",
                            media_type="text/css", content=style)
    epub_book.add_item(nav_css)
    # 保存
    try:
        epub.write_epub(path, epub_book)
        log.info(book.book_name + " epub导出成功!")
    except:
        log.info(book.book_name + " epub导出失败!")
        return
    # 推送
    if config.read("push_calibre")["enabled"]:
        push.calibre(book)


def build_txt(book: Book, chapter_list: Optional[Chapter]):
    if not chapter_list or not config.read("convert_txt"):
        return
    log.info(book.book_name + " 开始生成txt...")
    common.handle_title(book)
    path = config.read("txt_dir") + "/" + book.source + "/" + book.book_name + ".txt"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    txt_content = ""
    for chapter in chapter_list:
        # 跳过esj外链
        if chapter.chapter_id.startswith("http"):
            continue
        # 跳过打钱失败的章节
        if chapter.purchase_fail_flag and chapter.purchase_fail_flag == 1:
            continue
        # 跳过字数过少的章节
        if not chapter.content:
            continue
        if config.read("least_words") > 0 and config.read("least_words") > len(chapter.content):
            continue
        # 繁转简
        chapter_content = chapter.content
        if config.read('convert_hans'):
            chapter_content = zhconv.convert(chapter_content, 'zh-hans')
        # html转纯文字
        page_body = html.fromstring(chapter_content)
        content_list = page_body.xpath("//text()")
        content_list = [s.replace("\n", "") for s in content_list]
        content_list = [s for s in content_list if s]
        txt_content += chapter.chapter_name + "\n\n"
        txt_content += "\n".join(content_list) + "\n\n"
    # 写入
    with open(path, 'w', encoding='utf-8') as f:
        f.write(txt_content)
    log.info(book.book_name + " txt导出成功!")
