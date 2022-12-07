#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time : 2022/11/18 13:10
# @Author : chaocai

import json
import os
import re

from tenacity import retry, stop_after_attempt

from config import *
from service.login import *


async def mkdir(path):
    if not os.path.exists(path):
        os.makedirs(path)


def write_byte_data(path, byte):
    with open(path, 'wb') as f:
        f.write(byte)


def write_str_data(path, str):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(str)


async def write_miss_data(str):
    with open(SAVE_DIR + "missing.txt", 'a', encoding='utf-8') as f:
        f.write(str)


def get_split_str_list(start, end, str):
    return re.findall('(?<=%s).*?(?=%s)' % (start, end), str)


def format_text(str):
    return str.replace('/', '_').replace('.', '_').replace('?', '_').replace('\n', '')\
            .replace('\xa0', '').replace('\r', '').replace('\t', '')\
            .replace('\u3000', ' ').replace('\\u002F', '_').replace(':', '_').replace('*', '_')\
            .replace('<', '').replace('>', '').replace('"', '').replace('|', '').replace('\\', '')


def get_cost(str):
    return int(re.findall('\d+', str)[0])


async def save_pic_list(site_type, path, pic_list, session):
    if pic_list:
        for pic_url in pic_list:
            if not pic_url.startswith('http'):
                pic_url = URL_CONFIG[site_type + '_illustration'] % pic_url
            pic_name = pic_url.split('/')[-1].replace(':', '_').replace('*', '_')
            if '?' in pic_name:
                pic_name = pic_name.replace('?' + pic_url.split('?')[-1], '')
            pic_name = pic_name.replace('?', '_')
            pic_path = path + '_' + pic_name
            pic_res = await http_get_pic(pic_url, session, 'https://www.lightnovel.us/')
            if pic_res:
                write_byte_data(pic_path, pic_res)


@retry(stop=stop_after_attempt(RETRY_TIME))
async def http_get_text(site_type, url, session):
    # 请求头
    headers = HEADERS
    if site_type == 'oldlightnovel':
        headers['Referer'] = URL_CONFIG['oldlightnovel_varify']
    if site_type == 'lightnovel':
        headers['Cookie'] = '_ga=GA1.2.621722507.1669624080; token={%22security_key%22:%' \
                            + glo.get_value('gl_lightnovel_token') + '%22}'
    # 代理
    proxy = PROXIES_URL if PROXIES_URL else None
    try:
        response = await session.get(url=url, headers=headers, proxy=proxy, timeout=TIME_OUT)
        text = await response.text()
        if site_type == 'masiro':
            # 真白萌由于无法根据页数直接获取页面只有懒加载，抓目录时通过接口获取数据
            text = json.loads(text)
            text = text['html']
    except Exception as e:
        print('获取文字连接已断开，重试中... %s' % url)
        print(e)
        raise e
    return text


async def http_get_pic(url, session, referer=''):
    # 请求头
    headers = {
        'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
        'Accept-Encoding': HEADERS['Accept-Encoding'],
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'User-Agent': HEADERS['User-Agent']
    }
    if referer:
        headers['Referer'] = referer
    # 代理
    proxy = PROXIES_URL if PROXIES_URL else None
    pic = ''
    try:
        response = await session.get(url=url, headers=headers, proxy=proxy, timeout=TIME_OUT)
        pic = await response.read()
    except Exception:
        print('获取图片连接已断开 %s' % url)
        # 写入日志
        await write_miss_data('获取图片%s失败' % url + '\n')
    return pic
