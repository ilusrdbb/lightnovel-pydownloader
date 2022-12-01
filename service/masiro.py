#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time : 2022/11/30 15:20
# @Author : chaocai
import asyncio
import random

from lxml import html

from service.util import *


async def oldmasiro_get_book_list(session):
    book_urls = []
    for fid in OLD_MASIRO_FIDS:
        page_url = URL_CONFIG.get('oldmasiro_page') % fid
        text = await http_get_text('oldmasiro', page_url, session)
        page_body = html.fromstring(text)
        for book_url in page_body.xpath(XPATH_DICT['oldmasiro_page']):
            book_full_url = URL_CONFIG.get('oldmasiro_book') % book_url
            if book_full_url not in BLACK_LIST:
                book_urls.append(book_full_url)
    return book_urls


async def oldmasiro_get_book_data(book_url, page_body, session):
    # 获取书名
    book_data = {}
    book_data['_title'] = page_body.xpath(XPATH_DICT['oldmasiro_title'])
    # 获取页数
    if page_body.xpath(XPATH_DICT['oldmasiro_num']):
        page_num = get_cost(str(page_body.xpath(XPATH_DICT['oldmasiro_num'])[0]))
    else:
        page_num = 1
    # 章节 名称对地址
    chapter_list = []
    for num in range(1, page_num + 1):
        page_url = book_url + '&page=' + str(num)
        page_text = await http_get_text('', page_url, session)
        page_body = html.fromstring(page_text)
        for chapter_node in page_body.xpath(XPATH_DICT['oldmasiro_chapter']):
            chapter_node = html.fromstring(html.tostring(chapter_node))
            chapter_data = {'_index': chapter_node.xpath(XPATH_DICT['oldmasiro_chapter_name']),
                            '_url': chapter_node.xpath(XPATH_DICT['oldmasiro_chapter_url'])}
            chapter_list.append(chapter_data)
    book_data['_chapter'] = chapter_list
    if book_data['_title']:
        await save_oldmasiro_book(book_data, session)


async def save_oldmasiro_book(book_data, session):
    # TODO 写的究极烂，有空优化
    # 创建目录
    book_path = SAVE_DIR + 'oldmasiro/' + book_data['_title'][0]
    await mkdir(book_path)
    # 异步抓取章节
    for chapter_dict in book_data['_chapter']:
        if not chapter_dict['_index'] or not chapter_dict['_url']:
            continue
        # 处理下换行符等特殊符号
        chapter_dict['_index'][0] = format_text(chapter_dict['_index'][0])
        chapter_path = book_path + '/' + chapter_dict['_index'][0] + '.txt'
        if not os.path.exists(chapter_path) or ALWAYS_UPDATE_CHAPTER:
            # 睡眠
            if SLEEP_TIME > 0:
                await asyncio.sleep(random.random() * SLEEP_TIME)
            print('开始获取章节：%s 地址：%s' % (chapter_dict['_index'][0], chapter_dict['_url'][0]))
            text = await http_get_text('', URL_CONFIG['oldmasiro_content'] % chapter_dict['_url'][0], session)
            # 跳过权限不足
            if '抱歉，本帖要求阅读权限' not in text:
                page_body = html.fromstring(text)
                content_list = []
                pic_list = []
                # 只看楼主
                follow_url = page_body.xpath(XPATH_DICT['oldmasiro_follow'])[0]
                follow_text = await http_get_text('', follow_url, session)
                if follow_text:
                    follow_page_body = html.fromstring(follow_text)
                    # 获取页数
                    if follow_page_body.xpath(XPATH_DICT['oldmasiro_num']):
                        page_num = get_cost(str(follow_page_body.xpath(XPATH_DICT['oldmasiro_num'])[0]))
                    else:
                        page_num = 1
                    for num in range(1, page_num + 1):
                        content_url = follow_url + '&page=' + str(num)
                        content_text = await http_get_text('', content_url, session)
                        content_body = html.fromstring(content_text)
                        # 文字内容
                        content_in_list = content_body.xpath(XPATH_DICT['oldmasiro_content'])
                        content_list += content_in_list
                        # 插图
                        pic_in_list = content_body.xpath(XPATH_DICT['oldmasiro_illustration'])
                        pic_list += pic_in_list
                if content_list:
                    content = '\n'.join(content_list)
                    # 保存内容
                    write_str_data(chapter_path, content)
                    # 保存插画
                    await save_pic_list('oldmasiro', book_path + '/' + chapter_dict['_index'][0], pic_list, session)


async def masiro_pay(cost, object_id, session):
    print('%s 开始打钱：%s金币' % (object_id, cost))
    # 传参
    param_data = {
        'type': '2',
        'object_id': object_id,
        'cost': cost
    }
    # 请求头
    headers = {
        'User-Agent': HEADERS['User-Agent'],
        'x-csrf-token': glo.get_value('gl_masiro_token'),
        'x-requested-with': 'XMLHttpRequest'
    }
    # 代理
    proxy = PROXIES_URL if PROXIES_URL else None
    text = ''
    try:
        response = await session.post(url=URL_CONFIG['masiro_pay'], headers=headers, proxy=proxy,
                                      data=param_data, timeout=TIME_OUT)
        text = await response.text()
        print('打钱成功！')
    except Exception:
        print('%s打钱出错' % object_id)
    return text

