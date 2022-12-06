#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time : 2022/11/30 15:20
# @Author : chaocai
import asyncio
import random

from lxml import html

from service import glo
from service.util import *


async def _build_lightnovel_book(session):
    # 通过接口获取页
    for page in range(START_PAGE, MAX_PAGE + 1):
        page_json = await http_post_page(page, session)
        if page_json:
            book_list = page_json['data']['list']
            # 指定线程数
            thread_count = asyncio.Semaphore(MAX_THREAD)
            tasks = []
            for book in book_list:
                # 排除置顶
                if book['aid'] not in BLACK_AID_LIST:
                    tasks.append(_async_get_lightnovel_book(book, session, thread_count))
            await asyncio.wait(tasks)


async def _async_get_lightnovel_book(book, session, thread_count):
    async with thread_count:
        # 创建目录
        # 处理下换行符等特殊符号
        book['title'] = format_text(book['title'])
        book_path = SAVE_DIR + 'lightnovel/' + book['title'] + '_' + str(book['aid'])
        # 轻国的标题会变，根据aid判断是否存在同一目录，存在则重命名
        await lightnovel_mkdir(book_path, book)
        # 轻国分合集、非合集，非合集相当于只有一章的合集
        if book['sid'] == 0:
            # 非合集处理，直接跳转到目标页面
            await get_lightnovel_single(book_path, book, session)
        else:
            # 合集处理，先从合集获取章节再获取内容
            await get_lightnovel_chapter(book_path, book, session)


async def get_lightnovel_chapter(book_path, book, session):
    chapter_url = URL_CONFIG['lightnovel_book'] % book['sid']
    chapter_text = await http_get_text('lightnovel', chapter_url, session)
    chapter_body = html.fromstring(chapter_text)
    chapter_script_text = chapter_body.xpath('//script/text()')[0]
    # 正则获取章节地址和章节名
    chapter_list = await get_chapter_list(chapter_script_text, book)
    await get_lightnovel_content(book_path, chapter_list, session)


async def get_lightnovel_content(book_path, chapter_list, session, is_purchase=IS_PURCHASE):
    for chapter in chapter_list:
        # 处理下换行符等特殊符号
        chapter['title'] = format_text(chapter['title'])
        content_path = book_path + '/' + chapter['title'] + '.txt'
        if not os.path.exists(content_path) or ALWAYS_UPDATE_CHAPTER:
            # 睡眠
            if SLEEP_TIME > 0:
                await asyncio.sleep(random.random() * SLEEP_TIME)
            print('开始获取章节：%s 地址：%s' % (chapter['title'], chapter['url']))
            content_text = await http_get_text('lightnovel', chapter['url'], session)
            # 轻币打钱
            if '以下内容需要解锁观看' in content_text:
                if is_purchase:
                    content_body = html.fromstring(content_text)
                    cost_text = content_body.xpath('//button[contains(@class,\'unlock\')]/text()')[0]
                    cost = get_cost(cost_text)
                    if cost < MAX_PURCHASE:
                        await http_post_pay(chapter['aid'], cost, session)
                        await get_lightnovel_content(book_path, chapter_list, session, False)
            # 排除仅app
            elif '您可能没有访问权限' not in content_text:
                content_body = html.fromstring(content_text)
                # 文字内容
                content_list = content_body.xpath(XPATH_DICT['lightnovel_content'])
                content = '\n'.join(content_list)
                # 插画
                pic_list = content_body.xpath(XPATH_DICT['lightnovel_illustration'])
                # 保存内容
                write_str_data(content_path, content)
                # 保存插画
                await save_pic_list('lightnovel', book_path + '/' + chapter['title'], pic_list, session)


async def get_lightnovel_single(book_path, book, session, is_purchase=IS_PURCHASE):
    # 处理下换行符等特殊符号
    book['title'] = format_text(book['title'])
    content_path = book_path + '/' + book['title'] + '.txt'
    if not os.path.exists(content_path) or ALWAYS_UPDATE_CHAPTER:
        # 睡眠
        if SLEEP_TIME > 0:
            await asyncio.sleep(random.random() * SLEEP_TIME)
        content_url = URL_CONFIG['lightnovel_chapter'] % book['aid']
        print('开始获取章节：%s 地址：%s' % (book['title'], content_url))
        content_text = await http_get_text('lightnovel', content_url, session)
        # 轻币打钱
        if '以下内容需要解锁观看' in content_text:
            if is_purchase:
                content_body = html.fromstring(content_text)
                cost_text = content_body.xpath('//button[contains(@class,\'unlock\')]/text()')[0]
                cost = get_cost(cost_text)
                if cost < MAX_PURCHASE:
                    await http_post_pay(book['aid'], cost, session)
                    await get_lightnovel_single(book_path, book, session, False)
        # 排除仅app
        elif '您可能没有访问权限' not in content_text:
            content_body = html.fromstring(content_text)
            # 文字内容
            content_list = content_body.xpath(XPATH_DICT['lightnovel_content'])
            content = '\n'.join(content_list)
            # 插画
            pic_list = content_body.xpath(XPATH_DICT['lightnovel_illustration'])
            # 保存内容
            write_str_data(content_path, content)
            # 保存插画
            await save_pic_list('lightnovel', book_path + '/' + book['title'], pic_list, session)


@retry(stop=stop_after_attempt(RETRY_TIME))
async def http_post_page(page, session):
    url = URL_CONFIG['lightnovel_page']
    # 请求头
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Encoding': HEADERS['Accept-Encoding'],
        'Accept-Language': HEADERS['Accept-Language'],
        'User-Agent': HEADERS['User-Agent']
    }
    # 代理
    proxy = PROXIES_URL if PROXIES_URL else None
    # 传参
    param_data = {
        'client': 'web',
        'd': {
            'gid': 106,
            'page': page,
            'parent_gid': 3,
            'security_key': glo.get_value('gl_lightnovel_token')
        },
        'gz': 0,
        'is_encrypted': 0,
        'platform': 'pc',
        'sign': ''
    }
    try:
        response = await session.post(url=url, headers=headers, proxy=proxy, json=param_data, timeout=TIME_OUT)
        res_json = await response.json()
    except Exception as e:
        print('获取页面连接已断开，重试中...')
        raise e
    return res_json


async def http_post_pay(aid, cost, session):
    print('%d开始打钱：%d轻币' % (aid, cost))
    url = URL_CONFIG['lightnovel_pay']
    # 请求头
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Encoding': HEADERS['Accept-Encoding'],
        'Accept-Language': HEADERS['Accept-Language'],
        'User-Agent': HEADERS['User-Agent']
    }
    # 代理
    proxy = PROXIES_URL if PROXIES_URL else None
    # 传参
    param_data = {
        'client': 'web',
        'd': {
            'goods_id': 1,
            'number': 1,
            'params': aid,
            'price': cost,
            'security_key': glo.get_value('gl_lightnovel_token'),
            'total_price': cost
        },
        'gz': 0,
        'is_encrypted': 0,
        'platform': 'pc',
        'sign': ''
    }
    try:
        response = await session.post(url=url, headers=headers, proxy=proxy, json=param_data, timeout=TIME_OUT)
        if not response.status == 200:
            print('打钱失败！')
        print('打钱成功！')
    except Exception as e:
        print('打钱失败！')


async def lightnovel_mkdir(book_path, book):
    dir_list = os.listdir(SAVE_DIR + 'lightnovel/')
    if dir_list:
        rename_flag = False
        for dir in dir_list:
            if str(book['aid']) in dir:
                dir = SAVE_DIR + 'lightnovel/' + dir
                os.rename(dir, book_path)
                rename_flag = True
        if not rename_flag:
            os.makedirs(book_path)
    else:
        os.makedirs(book_path)


async def get_chapter_list(chapter_script_text, book):
    chapter_list = []
    # 有两种类型，正则尝试两次
    chapter_re = format_text('.aid=', '";', chapter_script_text)
    if chapter_re:
        for chapter_text in chapter_re:
            try:
                chapter = {'title': chapter_text.split('title="')[1],
                           'url': URL_CONFIG['lightnovel_chapter'] % int(chapter_text.split(';')[0]),
                           'aid': int(chapter_text.split(';')[0])}
                chapter_list.append(chapter)
            except Exception as e:
                continue
    else:
        chapter_re2 = format_text(',aid:', '",banner', chapter_script_text)
        if chapter_re2:
            for chapter_text in chapter_re2:
                try:
                    chapter = {'title': chapter_text.split('title:"')[1],
                               'url': URL_CONFIG['lightnovel_chapter'] % int(chapter_text.split(',title')[0]),
                               'aid': int(chapter_text.split(',title')[0])}
                    chapter_list.append(chapter)
                except Exception as e:
                    continue
    # 把自己加进去
    chapter_self = {'title': book['title'],
                    'url': URL_CONFIG['lightnovel_chapter'] % book['aid'],
                    'aid': book['aid']}
    chapter_list.append(chapter_self)


async def oldlightnovel_get_book_data(page_body, session):
    # 获取书名
    book_data = {}
    book_data['_title'] = page_body.xpath(XPATH_DICT['oldlightnovel_title'])
    print('开始抓取：%s' % book_data['_title'])
    # 只看楼主
    follow_url = URL_CONFIG['oldlightnovel_book'] % page_body.xpath(XPATH_DICT['oldlightnovel_follow'])[0]
    follow_text = await http_get_text('', follow_url, session)
    if follow_text:
        follow_page_body = html.fromstring(follow_text)
        # 第一页的全部内容
        chapter_list = follow_page_body.xpath(XPATH_DICT['oldlightnovel_chapter'])
        # 获取页数
        if follow_page_body.xpath(XPATH_DICT['oldlightnovel_num']):
            page_num = get_cost(str(follow_page_body.xpath(XPATH_DICT['oldlightnovel_num'])[0]))
            # 从第二页开始抓
            if page_num > 1:
                for num in range(2, page_num+1):
                    # 循环获取剩余页的内容
                    loop_url = URL_CONFIG['oldlightnovel_chapter'] % (follow_url, str(num))
                    loop_text = await http_get_text('', loop_url, session)
                    if loop_text:
                        loop_page_body = html.fromstring(loop_text)
                        chapter_list += loop_page_body.xpath(XPATH_DICT['oldlightnovel_chapter'])
        book_data['_chapter'] = chapter_list
        await save_oldlightnovel_book(book_data, session)


async def save_oldlightnovel_book(book_data, session):
    # 处理下换行符等特殊符号
    book_data['_title'][0] = format_text(book_data['_title'][0])
    # 创建目录
    book_path = SAVE_DIR + 'oldlightnovel/' + book_data['_title'][0]
    await mkdir(book_path)
    # 保存章节
    chapter_index = 1
    for chapter_text in book_data['_chapter']:
        chapter_path = book_path + '/' + str(chapter_index) + '.txt'
        if not os.path.exists(chapter_path) or ALWAYS_UPDATE_CHAPTER:
            chapter_body = html.fromstring(html.tostring(chapter_text))
            # 内容
            content_list = chapter_body.xpath(XPATH_DICT['oldlightnovel_content'])
            content = '\n'.join(content_list)
            # 图片
            pic_list = chapter_body.xpath(XPATH_DICT['oldlightnovel_illustration'])
            # 忽略字少章节，比如译者公告啥的
            if len(pic_list) < 2 and LEAST_WORDS > 0 and len(content) < LEAST_WORDS:
                continue
            else:
                # 保存内容
                write_str_data(chapter_path, content)
                # 保存插画
                await save_pic_list('oldlightnovel', book_path + '/' + str(chapter_index), pic_list, session)
        chapter_index += 1
