#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time : 2022/11/18 13:05
# @Author : chaocai
import asyncio
from random import random

import aiohttp

from service.util import *

"""
白名单爬取

:param site_type: 站点
"""


async def build_some_book(site_type):
    jar = aiohttp.CookieJar(unsafe=True)
    conn = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=conn, trust_env=True, cookie_jar=jar) as session:
        # 登录
        token = ''
        if REQUIRED_LOGIN:
            # 真白萌token
            if site_type == 'masiro':
                token = await http_get_token(URL_CONFIG[site_type + '_login'] % '', session)
            # 旧轻国验证码
            if site_type == 'oldlightnovel':
                login_hash = await http_get_code(URL_CONFIG[site_type + '_varify'], session)
                await http_login(site_type, login_hash['form_hash'], session, login_hash['login_hash'])
            else:
                await http_login(site_type, token, session)
        # 指定线程数
        thread_count = asyncio.Semaphore(MAX_THREAD)
        tasks = []
        for book_url in WHITE_LIST:
            tasks.append(_async_get_book_data(book_url, site_type, token, session, thread_count))
        await asyncio.wait(tasks)


"""
全局爬取

:param site_type: 站点
"""


async def build_all_book(site_type):
    jar = aiohttp.CookieJar(unsafe=True)
    conn = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=conn, trust_env=True, cookie_jar=jar) as session:
        # 登录
        token = ''
        if REQUIRED_LOGIN:
            # 真白萌token
            if site_type == 'masiro':
                token = await http_get_token(URL_CONFIG[site_type + '_login'] % '', session)
            # 旧轻国验证码
            if site_type == 'oldlightnovel':
                login_hash = await http_get_code(URL_CONFIG[site_type + '_varify'], session)
                await http_login(site_type, login_hash['form_hash'], session, login_hash['login_hash'])
            else:
                await http_login(site_type, token, session)
        await _build_all_book(site_type, token, session)


async def _build_all_book(site_type, token, session):
    book_urls = []
    # 开始页
    current_page = START_PAGE
    # 循环标识，用于跳出循环
    loop_flag = True
    # 循环目录获取每本书的地址
    while loop_flag:
        # 获取当前页
        print('开始获取第%d页' % current_page)
        page_url = URL_CONFIG.get(site_type + '_page') % current_page
        text = await http_get_text(site_type, page_url, session)
        # 尾页判断
        if not text:
            break
        # 解析当前页，获取当前页全部小说的地址列表
        page_body = html.fromstring(text)
        for book_url in page_body.xpath(XPATH_DICT[site_type + '_page']):
            book_full_url = URL_CONFIG.get(site_type + '_book') % book_url
            if book_full_url not in BLACK_LIST:
                book_urls.append(book_full_url)
        print('已获取第%d页。' % current_page)
        current_page += 1
        # 配置页数限制
        if current_page > MAX_PAGE:
            loop_flag = False
    # 有可能爬取的时候恰好小说更新翻到下一页，去重
    book_urls = list(set(book_urls))
    # 异步抓每本书
    # 指定线程数
    thread_count = asyncio.Semaphore(MAX_THREAD)
    tasks = []
    for book_url in book_urls:
        if book_url:
            tasks.append(_async_get_book_data(book_url, site_type, token, session, thread_count))
    await asyncio.wait(tasks)


"""
异步抓取书籍和章节信息

:param book_url: 书籍地址
:param site_type: 站点
:param token
:param session
:param thread_count: 指定线程数
"""


async def _async_get_book_data(book_url, site_type, token, session, thread_count):
    async with thread_count:
        text = await http_get_text('', book_url, session)
        if text:
            page_body = html.fromstring(text)
            # 旧论坛 页面-只看楼主-每一楼做一章
            if site_type == 'oldlightnovel':
                # 获取书名
                book_data = {}
                book_data['_title'] = page_body.xpath(XPATH_DICT[site_type + '_title'])
                print('开始抓取：%s' % book_data['_title'])
                # 只看楼主
                follow_url = URL_CONFIG[site_type + '_book'] % page_body.xpath(XPATH_DICT[site_type + '_follow'])[0]
                follow_text = await http_get_text('', follow_url, session)
                if follow_text:
                    follow_page_body = html.fromstring(follow_text)
                    # 第一页的全部内容
                    chapter_list = follow_page_body.xpath(XPATH_DICT[site_type + '_chapter'])
                    # 获取页数
                    if follow_page_body.xpath(XPATH_DICT[site_type + '_num']):
                        page_num = int(re.findall('\d+', str(follow_page_body.xpath(XPATH_DICT[site_type + '_num'])[0]))[0])
                        for num in range(page_num):
                            # 跳过第一页
                            if num > 1:
                                # 循环获取剩余页的内容
                                loop_url = URL_CONFIG[site_type + '_chapter'] % (follow_url, str(num))
                                loop_text = await http_get_text('', loop_url, session)
                                if loop_text:
                                    loop_page_body = html.fromstring(loop_text)
                                    chapter_list += loop_page_body.xpath(XPATH_DICT[site_type + '_chapter'])
                    book_data['_chapter'] = chapter_list
                    await save_forum_book(site_type, book_data, session)
            # 新论坛 页面-直接获取章节
            else:
                # 获取封面、书名、描述、章节、章节名
                book_data = {}
                for key in {'_title', '_cover', '_describe'}:
                    book_data[key] = page_body.xpath(XPATH_DICT[site_type + key])
                # 章节 名称对地址
                chapter_list = []
                for chapter_node in page_body.xpath(XPATH_DICT[site_type + '_chapter']):
                    chapter_node = html.fromstring(html.tostring(chapter_node))
                    chapter_data = {}
                    chapter_data['_index'] = chapter_node.xpath(XPATH_DICT[site_type + '_chapter_name'])
                    chapter_data['_url'] = chapter_node.xpath(XPATH_DICT[site_type + '_chapter_url'])
                    if site_type == 'masiro':
                        chapter_data['_cost'] = chapter_node.xpath('//a/@data-cost')
                        chapter_data['_payed'] = chapter_node.xpath('//a/@data-payed')
                        chapter_data['_id'] = chapter_node.xpath('//a/@data-id')
                    chapter_list.append(chapter_data)
                book_data['_chapter'] = chapter_list
                if book_data['_title']:
                    await save_book(site_type, book_data, token, session)


"""
保存书籍信息

:param site_type: 站点
:param book_data: 书籍信息
:param token
:param session
"""


async def save_book(site_type, book_data, token, session):
    # 创建目录
    book_path = SAVE_DIR + site_type + '/' + book_data['_title'][0]
    await mkdir(book_path)
    # 创建封面图
    cover_name = 'cover.jpg'
    cover_path = book_path + '/' + cover_name
    if not os.path.exists(cover_path) or ALWAYS_UPDATE_COVER:
        if book_data['_cover']:
            print('开始获取封面：%s' % book_data['_cover'][0])
            cover_res = await http_get_pic(URL_CONFIG.get(site_type + '_cover') % book_data['_cover'][0], session)
            if cover_res:
                write_byte_data(cover_path, cover_res)
    # 创建简介
    describe_name = '简介.txt'
    describe_path = book_path + '/' + describe_name
    if not os.path.exists(describe_path) or ALWAYS_UPDATE_COVER:
        if book_data['_describe']:
            print('开始获取简介：%s' % book_data['_title'][0])
            write_str_data(describe_path, ''.join(book_data['_describe']))
    # 异步抓取章节
    await save_chapter_data(site_type, book_data['_chapter'], book_path, token, session)


"""
论坛保存书籍

:param site_type: 站点
:param book_data: 书籍信息
:param session
"""


async def save_forum_book(site_type, book_data, session):
    # 处理下换行符等特殊符号
    book_data['_title'][0] = book_data['_title'][0].replace('/', '_').replace('\u3000','')\
        .replace('.','').replace('?','').replace(' ','')
    # 创建目录
    book_path = SAVE_DIR + site_type + '/' + book_data['_title'][0]
    await mkdir(book_path)
    # 保存章节
    chapter_index = 1
    for chapter_text in book_data['_chapter']:
        chapter_path = book_path + '/' + str(chapter_index) + '.txt'
        if not os.path.exists(chapter_path) or ALWAYS_UPDATE_CHAPTER:
            chapter_body = html.fromstring(html.tostring(chapter_text))
            # 内容
            content_list = chapter_body.xpath(XPATH_DICT[site_type + '_content'])
            content = '\n'.join(content_list)
            # 图片
            pic_list = chapter_body.xpath(XPATH_DICT[site_type + '_illustration'])
            # 忽略字少章节，比如译者公告啥的
            if len(pic_list) < 2 and LEAST_WORDS > 0 and len(content) < LEAST_WORDS:
                continue
            else:
                # 保存内容
                write_str_data(chapter_path, content)
                # 保存插画
                if pic_list:
                    pic_count = 1
                    for pic_url in pic_list:
                        if not pic_url.startswith('http'):
                            pic_url = URL_CONFIG[site_type + '_illustration'] % pic_url
                        if site_type == 'oldlightnovel':
                            pic_path = book_path + '/' + str(chapter_index) + '_' + str(pic_count) + '.jpg'
                        else:
                            pic_path = book_path + '/' + str(chapter_index) + '_' + pic_url.split('/')[-1]
                        pic_res = await http_get_pic(pic_url, session)
                        if pic_res:
                            write_byte_data(pic_path, pic_res)
                            pic_count += 1
        chapter_index += 1


"""
保存书籍章节

:param site_type: 站点
:param chapter_data: 章节信息
:param book_path: 书籍保存路径
:param token
:param session
"""


async def save_chapter_data(site_type, chapter_data, book_path, token, session):
    for chapter_dict in chapter_data:
        if not chapter_dict['_index'] or not chapter_dict['_url']:
            continue
        # 处理下换行符等特殊符号
        chapter_dict['_index'][0] = chapter_dict['_index'][0].replace('\n', '')\
            .replace('\xa0', '').replace('\r', '').replace('?', '').replace('/', '')\
            .replace('\t', '')
        chapter_path = book_path + '/' + chapter_dict['_index'][0] + '.txt'
        if not os.path.exists(chapter_path) or ALWAYS_UPDATE_CHAPTER:
            # 睡眠
            if SLEEP_TIME > 0:
                asyncio.sleep(random.random() * SLEEP_TIME)
            print('开始获取章节：%s 地址：%s' % (chapter_dict['_index'][0], chapter_dict['_url'][0]))
            # 真白萌先考虑打钱
            if site_type == 'masiro' and int(chapter_dict['_cost'][0]) > 0 and chapter_dict['_payed'][0] == '0':
                if IS_PURCHASE:
                    # 打钱！
                    pay_rep = await masiro_pay(chapter_dict['_cost'][0], chapter_dict['_id'][0], token, session)
                    if not pay_rep:
                        continue
                    print('打钱成功！')
                else:
                    # 买不起，不抓了
                    continue
            # esj考虑贴吧，做的比较粗糙因为我觉得抓贴吧的意义不大，贴吧的吞楼太厉害了，大概率啥也看不到
            if 'https://tieba.baidu.com' in chapter_dict['_url'][0]:
                # 只看楼主的第一页
                text = await http_get_text('', chapter_dict['_url'][0] + '?see_lz=1', session)
                page_body = html.fromstring(text)
                # 文字内容
                content_list = page_body.xpath(XPATH_DICT['tieba_content'])
                content = '\n'.join(content_list)
                if LEAST_WORDS > 0 and len(content) < LEAST_WORDS:
                    continue
                else:
                    # 保存内容
                    write_str_data(chapter_path, content)
            else:
                text = await http_get_text('', URL_CONFIG[site_type + '_content'] % chapter_dict['_url'][0], session)
                page_body = html.fromstring(text)
                # 文字内容
                content_list = page_body.xpath(XPATH_DICT[site_type + '_content'])
                content = '\n'.join(content_list)
                # 插画
                pic_list = page_body.xpath(XPATH_DICT[site_type + '_illustration'])
                # 忽略字少章节，比如译者公告啥的
                if len(pic_list) < 2 and LEAST_WORDS > 0 and len(content) < LEAST_WORDS:
                    continue
                else:
                    # 保存内容
                    write_str_data(chapter_path, content)
                    # 保存插画
                    if pic_list:
                        for pic_url in pic_list:
                            if not pic_url.startswith('http'):
                                pic_url = URL_CONFIG[site_type + '_illustration'] % pic_url
                            if not pic_url.startswith('http'):
                                # 真白萌的空图片比较特殊
                                continue
                            pic_path = book_path + '/' + chapter_dict['_index'][0] + '_' + pic_url.split('/')[-1]
                            pic_res = await http_get_pic(pic_url, session)
                            if pic_res:
                                write_byte_data(pic_path, pic_res)