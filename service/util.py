#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time : 2023/5/20
# @Author : chaocai
import asyncio
import base64
import json
import os
import random
import re
import zlib
from PIL import Image
import pillow_avif

from tenacity import retry, stop_after_attempt
from zhconv import zhconv

from service import config, log


# 正则获取两字符串之间的字符串
def get_split_str_list(start, end, str):
    return re.findall('(?<=%s).*?(?=%s)' % (start, end), str)


# 通用get请求
@retry(stop=stop_after_attempt(3))
async def http_get(url, headers, success_info, fail_info, session):
    if config.read('sleep_time') > 0 and not 'masiro' in url:
        await asyncio.sleep(random.random() * config.read('sleep_time'))
    elif 'masiro.' in url:
        await asyncio.sleep(5)
    proxy = config.read('proxy_url') if config.read('proxy_url') else None
    try:
        response = await session.get(url=url, headers=headers, proxy=proxy,
                                     timeout=config.read('time_out'))
        if not response.status == 200:
            raise Exception(fail_info) if fail_info else Exception()
        text = await response.text('utf-8', 'ignore')
        if success_info:
            log.info(success_info)
    except Exception as e:
        if fail_info:
            log.info(fail_info)
        raise e
    return text


# 通用post请求
@retry(stop=stop_after_attempt(3))
async def http_post(url, headers, param, success_info, fail_info, is_json, session):
    if config.read('sleep_time') > 0 and not 'masiro' in url:
        await asyncio.sleep(random.random() * config.read('sleep_time'))
    elif 'masiro.' in url:
        await asyncio.sleep(5)
    proxy = config.read('proxy_url') if config.read('proxy_url') else None
    try:
        if is_json:
            response = await session.post(url=url, headers=headers, proxy=proxy,
                                          json=param, timeout=config.read('time_out'))
        else:
            response = await session.post(url=url, headers=headers, proxy=proxy,
                                          data=param, timeout=config.read('time_out'))
        if not response.status == 200:
            raise Exception(fail_info) if fail_info else Exception()
        text = await response.text()
        if success_info:
            log.info(success_info)
    except Exception as e:
        if fail_info:
            log.info(fail_info)
        raise e
    return text


# flaresolverr请求
@retry(stop=stop_after_attempt(3))
async def http_flaresolverr_post(url, target, fail_info, session):
    proxy = config.read('proxy_url') if config.read('proxy_url') else None
    headers = {
        'content-type': 'application/json'
    }
    param_str = '{"cmd": "request.get","url": "'+target+'","maxTimeout": 60000}'
    try:
        response = await session.post(url=url, headers=headers, proxy=proxy, json=json.loads(param_str), timeout=120)
        if not response.status == 200:
            raise Exception(fail_info) if fail_info else Exception()
        text = await response.text()
    except Exception as e:
        if fail_info:
            log.info(fail_info)
        raise e
    return json.loads(text)['solution']


# 获取图片流
@retry(stop=stop_after_attempt(3))
async def http_get_pic(url, headers, session, msg=''):
    if 'masiro.' in url:
        await asyncio.sleep(5)
    proxy = config.read('proxy_url') if config.read('proxy_url') else None
    pic = None
    try:
        response = await session.get(url=url, headers=headers, proxy=proxy,
                                     timeout=config.read('time_out'))
        pic = await response.read()
    except Exception:
        log.info('获取图片连接已断开 %s' % url)
        # 写入日志
        write_miss_data('%s 获取图片%s失败' % (msg, url + '\n'))
    return pic


# 抓取图片失败记录
def write_miss_data(str):
    with open(config.read('txt_dir') + "missing.txt", 'a', encoding='utf-8') as f:
        f.write(str)


# 写二进制
def write_byte_data(path, byte):
    with open(path, 'wb') as f:
        f.write(byte)


# 通用构造请求头
def build_headers(login_info, is_pic = False, is_pay = False):
    headers = config.read('headers')
    if login_info.site == 'lightnovel' and not is_pic:
        headers = {}
        headers['user-agent'] = 'Dart/2.10 (dart:io)'
        headers['content-type'] = 'application/json; charset=UTF-8'
        headers['accept-encoding'] = 'gzip'
        headers['host'] = 'api.lightnovel.us'
    if is_pic:
        headers['Accept'] = 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8'
    if login_info.site == 'masiro':
        headers['origin'] = 'https://masiro.me'
        headers['referer'] = 'https://masiro.me/admin'
        headers['user-agent'] = login_info.ua
    if login_info.site == 'masiro' and is_pay:
        headers['x-csrf-token'] = login_info.token
    return headers


# 根据id查找对应路径下的文件或文件夹列表
def find_id_path(path, id):
    if not os.path.exists(path):
        os.makedirs(path)
        return []
    # 列出所有文件夹
    all_dirs = [os.path.join(path, name) for name in os.listdir(path)]
    result = [item for item in all_dirs if os.path.isdir(item)
              and '_' + id + '_' in os.path.basename(item) or '_' + id + '_' in item]
    return result


# 格式化标题文本
def format_text(str):
    return str.replace('/', '').replace('.', '，').replace('?', '？').replace('\t', '') \
        .replace(':', '：').replace('*', '').replace('<', '《').replace('>', '》') \
        .replace('\r', '').replace('\n', '').replace('\xa0', '').replace(' ', '') \
        .replace('"', '“').replace('|', '').replace('\\', '').replace('_', '').replace('#', '') \
        .replace('\x1c', '')


# 写入文本
def write_str_data(path, str):
    if config.read('convert_hans'):
        str = zhconv.convert(str, 'zh-hans')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(str)


# gzip解压
def unzip(str):
    b = base64.b64decode(str)
    s = zlib.decompress(b).decode()
    return json.loads(s)


# avif转png
def convert_avif_png(path):
    output_path = None
    try:
        avif_image = Image.open(path)
        png_image = avif_image.convert('RGB')
        output_path = os.path.splitext(path)[0] + '.png'
        png_image.save(output_path, 'PNG')
        avif_image.close()
        png_image.close()
    except:
        pass
    os.remove(path)
    return output_path