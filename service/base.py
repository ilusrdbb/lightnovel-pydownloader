#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time : 2022/11/18 13:05
# @Author : chaocai

import asyncio
from random import random

import aiohttp
from lxml import html

from service.lightnovel import _build_lightnovel_book, oldlightnovel_get_book_data
from service.login import *
from service.masiro import *
from service.util import *


async def build_some_book(site_type):
    jar = aiohttp.CookieJar(unsafe=True)
    conn = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=conn, trust_env=True, cookie_jar=jar) as session:
        # 登录
        if REQUIRED_LOGIN:
            await start_login(site_type, session)
        # 指定线程数
        thread_count = asyncio.Semaphore(MAX_THREAD)
        tasks = []
        for book_url in WHITE_LIST:
            tasks.append(_async_get_book_data(book_url, site_type, session, thread_count))
        await asyncio.wait(tasks)


async def build_all_book(site_type):
    jar = aiohttp.CookieJar(unsafe=True)
    conn = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=conn, trust_env=True, cookie_jar=jar) as session:
        # 登录
        if REQUIRED_LOGIN:
            await start_login(site_type, session)
        if site_type == 'lightnovel':
            # 轻国新站属实逻辑特殊，独立出模块处理
            await _build_lightnovel_book(session)
        else:
            await _build_all_book(site_type, session)


async def _build_all_book(site_type, session):
    book_urls = []
    # 真白萌旧站循环大板块获取
    if site_type == 'oldmasiro':
        print('开始获取')
        book_urls = await oldmasiro_get_book_list(session)
    # 其余正常根据页数循环
    else:
        for page_num in range(START_PAGE, MAX_PAGE+1):
            print('开始获取第%d页' % page_num)
            page_url = URL_CONFIG.get(site_type + '_page') % page_num
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
    # 有可能爬取的时候恰好小说更新翻到下一页，去重
    book_urls = list(set(book_urls))
    # 异步抓每本书
    thread_count = asyncio.Semaphore(MAX_THREAD)
    tasks = []
    for book_url in book_urls:
        if book_url:
            tasks.append(_async_get_book_data(book_url, site_type, session, thread_count))
    await asyncio.wait(tasks)


async def _async_get_book_data(book_url, site_type, session, thread_count):
    async with thread_count:
        text = await http_get_text('', book_url, session)
        if text:
            page_body = html.fromstring(text)
            # 轻国旧论坛 页面-只看楼主-每一楼做一章
            if site_type == 'oldlightnovel':
                await oldlightnovel_get_book_data(page_body, session)
            # 真白萌旧站 页面-分页循环获取章节-只看楼主全部内容做一章
            elif site_type == 'oldmasiro':
                await oldmasiro_get_book_data(book_url, page_body, session)
            # 真白萌新站 esj 页面-直接获取章节
            else:
                # 获取封面、书名、描述、章节、章节名
                book_data = {}
                for key in {'_title', '_cover', '_describe'}:
                    book_data[key] = page_body.xpath(XPATH_DICT[site_type + key])
                # 章节 名称对地址
                chapter_list = []
                for chapter_node in page_body.xpath(XPATH_DICT[site_type + '_chapter']):
                    chapter_node = html.fromstring(html.tostring(chapter_node))
                    chapter_data = {'_index': chapter_node.xpath(XPATH_DICT[site_type + '_chapter_name']),
                                    '_url': chapter_node.xpath(XPATH_DICT[site_type + '_chapter_url'])}
                    if site_type == 'masiro':
                        chapter_data['_cost'] = chapter_node.xpath('//a/@data-cost')
                        chapter_data['_payed'] = chapter_node.xpath('//a/@data-payed')
                        chapter_data['_id'] = chapter_node.xpath('//a/@data-id')
                    chapter_list.append(chapter_data)
                book_data['_chapter'] = chapter_list
                if book_data['_title']:
                    await save_book(site_type, book_data, session)


async def save_book(site_type, book_data, session):
    book_data['_title'][0] = format_text(book_data['_title'][0])
    # 创建目录
    book_path = SAVE_DIR + site_type + '/' + book_data['_title'][0]
    await mkdir(book_path)
    # 创建封面图
    cover_name = 'cover.jpg'
    cover_path = book_path + '/' + cover_name
    if not os.path.exists(cover_path) or ALWAYS_UPDATE_COVER:
        if book_data['_cover']:
            cover_res = await http_get_pic(URL_CONFIG.get(site_type + '_cover') % book_data['_cover'][0], session)
            if cover_res:
                write_byte_data(cover_path, cover_res)
    # 创建简介
    describe_name = '简介.txt'
    describe_path = book_path + '/' + describe_name
    if not os.path.exists(describe_path) or ALWAYS_UPDATE_COVER:
        if book_data['_describe']:
            write_str_data(describe_path, ''.join(book_data['_describe']))
    # 抓取章节
    await save_chapter_data(site_type, book_data['_chapter'], book_path, session)


async def save_chapter_data(site_type, chapter_data, book_path, session):
    for chapter_dict in chapter_data:
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
            # 真白萌先考虑打钱
            if site_type == 'masiro' and int(chapter_dict['_cost'][0]) > 0 and chapter_dict['_payed'][0] == '0':
                if IS_PURCHASE:
                    if int(chapter_dict['_cost'][0]) < MAX_PURCHASE:
                        pay_rep = await masiro_pay(chapter_dict['_cost'][0], chapter_dict['_id'][0], session)
                        if not pay_rep:
                            continue
                else:
                    continue
            # esj考虑贴吧，做的比较粗糙因为我觉得抓贴吧的意义不大，贴吧的吞楼太厉害了，大概率啥也看不到
            if 'tieba.baidu.com' in chapter_dict['_url'][0]:
                # 贴吧有验证码，暂不考虑
                write_str_data(chapter_path, chapter_dict['_url'][0])
            elif 'www.ptt.cc' in chapter_dict['_url'][0]:
                text = await http_get_text('', chapter_dict['_url'][0], session)
                page_body = html.fromstring(text)
                # 文字内容
                content_list = page_body.xpath(XPATH_DICT['ptt_content'])
                content = '\n'.join(content_list)
                if LEAST_WORDS > 0 and len(content) < LEAST_WORDS:
                    continue
                else:
                    write_str_data(chapter_path, content)
            elif 'gitlab.com' in chapter_dict['_url'][0]:
                write_str_data(chapter_path, chapter_dict['_url'][0])
            elif 'www.bilibili.com' in chapter_dict['_url'][0]:
                text = await http_get_text('', chapter_dict['_url'][0], session)
                page_body = html.fromstring(text)
                # 文字内容
                content_list = page_body.xpath(XPATH_DICT['bilibili_content'])
                content = '\n'.join(content_list)
                if LEAST_WORDS > 0 and len(content) < LEAST_WORDS:
                    continue
                else:
                    write_str_data(chapter_path, content)
            elif 'anonymousfiles.cc' in chapter_dict['_url'][0]:
                text = await http_get_text('', chapter_dict['_url'][0], session)
                page_body = html.fromstring(text)
                # 文字内容
                content_list = page_body.xpath(XPATH_DICT['anonymousfiles_content'])
                content = '\n'.join(content_list)
                if LEAST_WORDS > 0 and len(content) < LEAST_WORDS:
                    continue
                else:
                    write_str_data(chapter_path, content)
            elif 'twitter.com' in chapter_dict['_url'][0]:
                write_str_data(chapter_path, chapter_dict['_url'][0])
            elif 'ncode.syosetu.com' in chapter_dict['_url'][0]:
                write_str_data(chapter_path, chapter_dict['_url'][0])
            elif 'www.qinxiaoshuo.com' in chapter_dict['_url'][0]:
                write_str_data(chapter_path, chapter_dict['_url'][0])
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
                    await save_pic_list(site_type, book_path + '/' + chapter_dict['_index'][0] , pic_list, session)
