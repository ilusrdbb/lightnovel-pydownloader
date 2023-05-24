#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time : 2023/5/20
# @Author : chaocai
import os

from ebooklib import epub
from zhconv import zhconv

from service import config


# 构造epub，方法有些长懒得拆先这样吧
def build_epub(book_data):
    path = config.read('epub_dir') + book_data.site + '/' + book_data.title + '.epub'
    if not os.path.exists(config.read('epub_dir') + book_data.site):
        os.makedirs(config.read('epub_dir') + book_data.site)
    print(book_data.title + "，开始生成epub...")
    book = epub.EpubBook()
    # 元数据
    book.set_identifier(book_data.id)
    book.set_title(book_data.title)
    book.set_language('cn')
    if book_data.author:
        book.add_author(book_data.author)
    if book_data.introduction:
        description = '\n'.join(book_data.introduction)
        description = zhconv.convert(description, 'zh-hans') if config.read('convert_hans') else description
        book.add_metadata('DC', 'description', description)
    book.add_metadata('DC', 'source', book_data.site)
    book.add_metadata('DC', 'rights', '本电子书由lightnovel-pydownloader制作生成，仅供个人使用，不得对外传播以及用于商业用途。')
    if book_data.tags:
        book.add_metadata('DC', 'subject', ';'.join(book_data.tags))
    if book_data.cover:
        # 设置封面
        book.set_cover("cover.jpg", open(book_data.cover[0], 'rb').read())
    # 章节
    chapters = book_data.chapter
    if chapters:
        book_chapters = []
        for chapter_data in chapters:
            chapter = epub.EpubHtml(title=chapter_data.title,
                                    file_name=chapter_data.id + '_' + chapter_data.title + '.xhtml', lang='cn')
            content = '\n'.join(chapter_data.content)
            content = zhconv.convert(content, 'zh-hans') if config.read('convert_hans') else content
            if config.read('least_words') > 0 and len(content) < config.read('least_words') \
                    and not chapter_data.pic:
                continue
            content_list = ['<p>' + item + '</p>' for item in content.split('\n')]
            if chapter_data.pic:
                for pic in chapter_data.pic:
                    image_content = open(pic, "rb").read()
                    if config.read('least_pic') > 0 and len(image_content) < config.read('least_pic'):
                        continue
                    image_name = pic.replace('\\', '/').split('/')[-1]
                    image_type = image_name.split('.')[-1]
                    image = epub.EpubImage(uid=image_name, file_name='Image/' + image_name,
                                           media_type='image/' + image_type, content=image_content)
                    book.add_item(image)
                    # 章节末尾插入图片
                    content_list.append('<img src="%s"/>' % ('../Image/' + image_name))
            chapter.content = ''.join(content_list)
            book.add_item(chapter)
            book_chapters.append(chapter)
    # 目录和书脊
    if book_chapters:
        book.toc = book_chapters
        book.spine = book_chapters
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
    # css
    style = 'body { font-family: Times, Times New Roman, serif; }'
    nav_css = epub.EpubItem(uid="style_nav", file_name="style/nav.css",
                            media_type="text/css", content=style)
    book.add_item(nav_css)
    # 保存
    epub.write_epub(path, book)
    print('epub已导出!')
