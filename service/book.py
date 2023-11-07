#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time : 2023/5/20
# @Author : chaocai
import asyncio
import json
import os
import re

from lxml import html
from zhconv import zhconv

from js.runjs import get_dsign
from service import config, util, chapter, epub, log


class Book:
    # 站点
    site: None
    # id
    id: None
    # 标题
    title: None
    # 作者
    author: None
    # 标签
    tags: None
    # 封面地址或路径
    cover: None
    # 简介
    introduction: None
    # 章节
    chapter: None
    # 路径
    path: None
    # 译者id，百合会需要
    author_id: None
    # 最大顺序号，百合会需要
    max_order: None
    # aid，轻国需要
    aid: None
    # sid，轻国需要
    sid: None

    # 初始化
    def __init__(self, site, id, title, author, tags, cover, introduction):
        self.site = site
        self.id = id
        title = util.format_text(title)
        self.title = zhconv.convert(title, 'zh-hans') if config.read('convert_hans') else title
        self.author = author
        self.tags = tags
        self.cover = cover
        self.introduction = introduction
        self.path = config.read('txt_dir') + self.site + '/' + self.title + '_' + self.id + '_'


# 异步抓取书籍
async def build_book(login_info, book_urls, session):
    thread_count = asyncio.Semaphore(config.read('max_thread'))
    if login_info.site == 'masiro':
        thread_count = asyncio.Semaphore(1)
    tasks = []
    for book_url in book_urls:
        if book_url:
            tasks.append(async_build_book(login_info, book_url, session, thread_count))
    if tasks:
        await asyncio.wait(tasks)


# 构造书籍元数据，获取书籍下全部章节并抓取
async def async_build_book(login_info, book_url, session, thread_count):
    async with thread_count:
        text = await util.http_get(book_url, util.build_headers(login_info), None,
                                   '书籍连接已断开，重试中... %s' % book_url, session)
        if login_info.site == 'yuri' and text.startswith('<script'):
            # 反爬处理
            new_book_url = 'https://bbs.yamibo.com' + get_dsign(text)
            text = await util.http_get(new_book_url, util.build_headers(login_info), None,
                                       '书籍连接已断开，重试中... %s' % book_url, session)
        page_body = html.fromstring(text)
        if login_info.site == 'oldlightnovel' or login_info.site == 'yuri':
            try:
                book_data = Book(login_info.site, get_book_id(login_info, book_url),
                                 page_body.xpath(config.read('xpath_config')[login_info.site]['title'])[0],
                                 None, None, None, None)
            except:
                # 跳过权限不足的
                return
            book_data.author_id = page_body.xpath(config.read('xpath_config')[login_info.site]['author'])[0]
            book_data.max_order = 0
            book_data.chapter = []
        else:
            author = None
            if page_body.xpath(config.read('xpath_config')[login_info.site]['author']):
                author = page_body.xpath(config.read('xpath_config')[login_info.site]['author'])[0]
            if not page_body.xpath(config.read('xpath_config')[login_info.site]['title']):
                # 跳过无标题的书籍
                return
            book_data = Book(login_info.site, get_book_id(login_info, book_url),
                             page_body.xpath(config.read('xpath_config')[login_info.site]['title'])[0],
                             author,
                             page_body.xpath(config.read('xpath_config')[login_info.site]['tags']),
                             page_body.xpath(config.read('xpath_config')[login_info.site]['cover']),
                             page_body.xpath(config.read('xpath_config')[login_info.site]['introduction']))
        # 生成文件夹
        create_book_dir(book_data)
        # 写入简介
        if book_data.introduction:
            util.write_str_data(book_data.path + '/简介.txt', '\n'.join(book_data.introduction))
        # 下载封面
        if book_data.cover:
            await download_cover(login_info, book_data, session)
        # 获取章节
        chapter_url_list = page_body.xpath(config.read('xpath_config')[login_info.site]['chapter'])
        if chapter_url_list:
            book_data.chapter = []
            order = 1
            for chapter_url in chapter_url_list:
                if login_info.site == 'masiro':
                    chapter_url = 'https://masiro.me' + chapter_url
                chapter_data = chapter.Chapter(None, chapter_url, None, None, order, None)
                # 抓取章节
                await chapter.build_chapter(login_info, book_data, chapter_data, session)
                book_data.chapter.append(chapter_data)
                order += 1
        elif login_info.site == 'oldlightnovel' or login_info.site == 'yuri':
            # 百合会 只看楼主-抓楼层做章节
            await chapter.build_discuz_chapter(login_info, book_data, session)
        # 生成epub
        if config.read('generate_epub'):
            epub.build_epub(book_data)


# 下载书籍封面
async def download_cover(login_info, book_data, session):
    if book_data.cover:
        path = book_data.path + '/cover.jpg'
        url = book_data.cover[0]
        if login_info.site == 'masiro':
            url = 'https://masiro.me' + url
        pic = await util.http_get_pic(url, util.build_headers(login_info, True, False), session)
        if pic:
            util.write_byte_data(path, pic)
            book_data.cover = [path]
        else:
            book_data.cover = None


# 处理书籍文件夹，应对标题更改的情况
def create_book_dir(book_data):
    # 找路径下是否存在同id的文件夹
    old_dir_path = util.find_id_path(config.read('txt_dir') + book_data.site, book_data.id)
    if not old_dir_path:
        # 没找到文件夹，新生成文件夹
        os.makedirs(book_data.path)
    else:
        old_dir_path = old_dir_path[0]
        # 新旧标题不同，重命名该文件夹
        if book_data.title != old_dir_path.split('/')[-1].split('_')[0]:
            os.rename(old_dir_path, book_data.path)
            # 重命名epub
            old_epub_path = config.read('epub_dir') + book_data.site + '/' + old_dir_path.split('_')[1] + '.epub'
            new_epub_path = config.read('epub_dir') + book_data.site + '/' + book_data.title + '.epub'
            if os.path.exists(old_epub_path):
                os.rename(old_epub_path, new_epub_path)


# 获取书籍id
def get_book_id(login_info, book_url):
    if login_info.site == 'esj':
        return re.search(r'/(\d+)\.html$', book_url).group(1)
    if login_info.site == 'masiro':
        return book_url.split('?novel_id=')[-1]
    if login_info.site == 'oldlightnovel' or login_info.site == 'yuri':
        return book_url.split('-')[1]


# 轻国特殊逻辑
async def lightnovel_build_book(login_info, session):
    book_data_list = []
    for page_num in range(config.read('start_page'), config.read('end_page') + 1):
        log.info('开始获取第%d页' % page_num)
        page_url = config.read('url_config')[login_info.site]['page']
        # gid 106 最新 gid 107 整卷
        param_str = '{"platform":"android","client":"app","sign":"","ver_name":"0.11.50","ver_code":190,' \
                    '"d":{"parent_gid":3,"gid":106,"page":' + str(page_num) + ',"pageSize":40,' \
                    '"security_key":"' + login_info.token + '"},"gz":1}'
        if config.read('get_collection'):
            page_url = config.read('url_config')[login_info.site]['collection']
            # 收藏页 class 1 单本 class 2 合集
            param_str = '{"platform":"android","client":"app","sign":"","ver_name":"0.11.50","ver_code":190,' \
                        '"d":{"uid":' + str(login_info.uid) + ',"page":' + str(page_num) + ',"type":1,' \
                        '"class":' + str(config.read('lightnovel_collection_class')) + ',"pageSize":20,' \
                        '"security_key":"' + login_info.token + '"},"gz":1}'
        text = await util.http_post(page_url, util.build_headers(login_info), json.loads(param_str), None,
                                    '页面连接已断开，重试中... ', True, session)
        book_list = util.unzip(text)['data']['list']
        black_aid = [969547, 1113228, 1099310, 1048596]
        for book in book_list:
            book_id = str(book['aid']) if book['sid'] == 0 else str(book['sid'])
            title = util.format_text(str(book['title']))
            # linux 文件长度限制
            if len(title) > 70:
                title = title[:70]
            title = zhconv.convert(title, 'zh-hans') if config.read('convert_hans') else title
            book_data = Book(login_info.site, book_id, title, None, None, [book['cover']], None)
            book_data.aid = book['aid']
            book_data.sid = book['sid']
            if book_data.aid not in black_aid:
                # 获取目录
                if book_data.sid != 0:
                    await lightnovel_get_category(login_info, book_data, session)
                else:
                    single_chapter = chapter.Chapter(str(book_data.aid), None, book_data.title, None, 1, None)
                    book_data.chapter = [single_chapter]
                # 生成文件夹
                create_book_dir(book_data)
                # 写入简介
                if book_data.introduction:
                    util.write_str_data(book_data.path + '/简介.txt', '\n'.join(book_data.introduction))
                # 下载封面
                if book_data.cover:
                    await download_cover(login_info, book_data, session)
                book_data_list.append(book_data)
    thread_count = asyncio.Semaphore(config.read('max_thread'))
    tasks = []
    for book_data in book_data_list:
        if book_data.chapter:
            tasks.append(async_lightnovel_book(login_info, book_data, session, thread_count))
    await asyncio.wait(tasks)


async def lightnovel_get_category(login_info, book_data, session):
    page_url = config.read('url_config')[login_info.site]['book']
    param_str = '{"platform":"android","client":"app","sign":"","ver_name":"0.11.50","ver_code":190,' \
                '"d":{"sid":' + str(book_data.sid) + ',"security_key":"' + login_info.token + '"},"gz":1}'
    text = await util.http_post(page_url, util.build_headers(login_info), json.loads(param_str), None,
                                '页面连接已断开，重试中... ', True, session)
    text_data = util.unzip(text)['data']
    if text_data:
        book_data.title = str(text_data['name'])
        book_data.introduction = [text_data['intro']]
        book_data.chapter = []
        for chapter_text in text_data['articles']:
            chapter_data = chapter.Chapter(str(chapter_text['aid']), None, str(chapter_text['title']), None,
                                           chapter_text['order'], None)
            chapter_data.title = util.format_text(chapter_data.title)
            if len(chapter_data.title) > 70:
                chapter_data.title = chapter_data.title[:70]
            chapter_data.title = zhconv.convert(chapter_data.title, 'zh-hans') if config.read(
                'convert_hans') else chapter_data.title
            book_data.chapter.append(chapter_data)
    else:
        book_data.chapter = []


# 异步抓取轻国章节
async def async_lightnovel_book(login_info, book_data, session, thread_count):
    async with thread_count:
        for chapter_data in book_data.chapter:
            await chapter.build_chapter(login_info, book_data, chapter_data, session)
    # 生成epub
    if config.read('generate_epub'):
        epub.build_epub(book_data)
