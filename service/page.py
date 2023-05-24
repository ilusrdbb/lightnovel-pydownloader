#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time : 2023/5/20
# @Author : chaocai
import json

from lxml import html

from service import config, book, util


# 抓取页数据
async def get_page(login_info, session):
    if login_info.site == 'lightnovel':
        await book.lightnovel_build_book(login_info, session)
        return
    else:
        book_urls = await common_get_page(login_info, session)
    # 有可能爬取的时候恰好小说更新翻到下一页，去重
    book_urls = list(set(book_urls))
    await book.build_book(login_info, book_urls, session)


# 通用抓取
async def common_get_page(login_info, session):
    book_urls = []
    for page_num in range(config.read('start_page'), config.read('end_page') + 1):
        print('开始获取第%d页' % page_num)
        page_url = config.read('url_config')[login_info.site]['page'] % page_num
        text = await util.http_get(page_url, util.build_headers(login_info), None,
                                    '页面连接已断开，重试中... %s' % page_url, session)
        if login_info.site == 'masiro':
            text = json.loads(text)['html']
        page_body = html.fromstring(text)
        for book_url in page_body.xpath(config.read('xpath_config')[login_info.site]['page']):
            book_full_url = config.read('url_config')[login_info.site]['book'] % book_url
            if book_full_url not in config.read('black_list'):
                book_urls.append(book_full_url)
    return book_urls

