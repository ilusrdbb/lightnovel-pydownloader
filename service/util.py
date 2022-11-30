#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time : 2022/11/18 13:10
# @Author : chaocai

import json
import os
import random
import re

from lxml import html
from tenacity import retry, stop_after_attempt

from service.config import *
from service.runjs import js_md5

"""
创建文件夹

:param path: 路径
"""


async def mkdir(path):
    if not os.path.exists(path):
        os.makedirs(path)


"""
写入byte数据，比如写入图片

:param path: 路径
:param byte: byte数据
"""


def write_byte_data(path, byte):
    with open(path, 'wb') as f:
        f.write(byte)


"""
写入字符串数据

:param path: 路径
:param str: 字符串数据
"""


def write_str_data(path, str):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(str)


"""
写入爬取错误信息

:param str: 错误信息
"""


async def write_miss_data(str):
    with open(SAVE_DIR + "missing.txt", 'a', encoding='utf-8') as f:
        f.write(str)


"""
http get 网页

:param site_type: 站点
:param url: 地址
:param session

:return 网页html字符串
"""


@retry(stop=stop_after_attempt(RETRY_TIME))
async def http_get_text(site_type, url, session):
    # 请求头
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'User-Agent': USER_AGENT
    }
    if site_type == 'oldlightnovel':
        headers['Referer'] = 'https://obsolete.lightnovel.us/member.php?mod=logging&action=login'
    # 代理
    proxy = PROXIES_URL if PROXIES_URL else None
    try:
        response = await session.get(url=url, headers=headers, proxy=proxy, timeout=TIME_OUT)
        text = await response.text()
        if site_type == 'masiro':
            # 真白萌由于无法根据页数直接获取页面只有懒加载，抓目录时通过接口获取数据
            text = json.loads(text)
            text = text["html"]
    except Exception as e:
        print('获取文字连接已断开，重试中... %s' % url)
        raise e
    return text


"""
http get 图片

:param url: 地址
:param session

:return 图片二进制流
"""


async def http_get_pic(url, session, referer=''):
    # 请求头
    headers = {
        'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'User-Agent': USER_AGENT,
        'Referer': referer,
    }
    # 代理
    proxy = PROXIES_URL if PROXIES_URL else None
    try:
        response = await session.get(url=url, headers=headers, proxy=proxy, timeout=TIME_OUT)
        pic = await response.read()
    except Exception:
        print('获取图片连接已断开 %s' % url)
        # 写入日志
        await write_miss_data('获取图片%s失败' % url + '\n')
        pic = ''
    return pic


"""
真白萌 购买接口

:param cost: 花费
:param object_id: 章节id
:param session

:return 接口响应
"""


async def masiro_pay(cost, object_id, token, session):
    print('%s 开始打钱：%s金币' % (object_id, cost))
    # 传参
    param_data = {'type': '2', 'object_id': object_id, 'cost': cost}
    # 请求头
    headers = {
        'User-Agent': USER_AGENT,
        'x-csrf-token': token,
        'x-requested-with': 'XMLHttpRequest'
    }
    # 代理
    proxy = PROXIES_URL if PROXIES_URL else None
    try:
        response = await session.post(url='https://masiro.me/admin/pay', headers=headers, proxy=proxy,
                                      data=param_data, timeout=TIME_OUT)
        text = await response.text()
    except Exception:
        print('%s打钱出错' % object_id)
    return text


"""
登录

:param site_type: 站点
:param session
:login_hash
"""


async def http_login(site_type, token, session, login_hash=''):
    print('开始登录...')
    url = URL_CONFIG[site_type + '_login'] % login_hash
    # 传参
    if site_type == 'masiro':
        param_data = {
            'username': LOGIN_INFO['username'],
            'password': LOGIN_INFO['password'],
            'remember': '1'
        }
    if site_type == 'esj':
        param_data = {
            'email': LOGIN_INFO['username'],
            'pwd': LOGIN_INFO['password'],
            'remember_me': 'on'
        }
    if site_type == 'oldlightnovel':
        md5_pwd = await js_md5(LOGIN_INFO['password'])
        param_data = {
            'formhash': token,
            'referer': 'https://obsolete.lightnovel.us/thread-1029685-1-1.html',
            'username': LOGIN_INFO['username'],
            'password': md5_pwd,
            'questionid': '0',
            'answer': '',
            'seccodehash': 'cS',
            'seccodemodid': 'member::logging',
            'cookietime': '2592000',
        }
        # 此时输入验证码
        print('请输入验证码：')
        code = input()
        param_data['seccodeverify'] = code
    if site_type == 'oldmasiro':
        param_data = {
            'username': LOGIN_INFO['username'],
            'password': LOGIN_INFO['password'],
            'fastloginfield': 'username',
            'cookietime': '2592000',
            'quickforward': 'yes',
            'handlekey': 'ls'
        }
    # 请求头
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'User-Agent': USER_AGENT
    }
    # 真白萌token
    if site_type == 'masiro':
        param_data['_token'] = token
        headers['x-csrf-token'] = token
        headers['x-requested-with'] = 'XMLHttpRequest'
    # 代理
    proxy = PROXIES_URL if PROXIES_URL else None
    try:
        response = await session.post(url=url, headers=headers, proxy=proxy, data=param_data, timeout=TIME_OUT)
        if not response.status == 200:
            raise Exception('登录失败！')
        text = await response.text()
        if '验证码填写错误' in text:
            raise Exception('验证码错误！')
        print('登录成功！')
    except Exception as e:
        print('登录失败！')
        raise e


"""
真白萌获取token

:param url: 地址
:param session

:return token字符串
"""


async def http_get_token(url, session):
    print('开始获取token...')
    # 请求头
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        'User-Agent': USER_AGENT
    }
    # 代理
    proxy = PROXIES_URL if PROXIES_URL else None
    try:
        response = await session.get(url=url, headers=headers, proxy=proxy, timeout=TIME_OUT)
        if not response.status == 200:
            raise Exception('获取token失败！')
        text = await response.text()
        page_body = html.fromstring(text)
        token = str(page_body.xpath('//input[@class=\'csrf\']/@value')[0])
    except Exception as e:
        print('获取token失败！')
        raise e
    return token


"""
旧轻国获取验证码，写入至./books/code.jpg中

:param url: 地址
:param session

:return hash
"""


async def http_get_code(url, session):
    print('开始获取验证码...')
    # 请求头
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'User-Agent': USER_AGENT,
        'Referer': 'https://obsolete.lightnovel.us/thread-1029685-1-1.html'
    }
    # 代理
    proxy = PROXIES_URL if PROXIES_URL else None
    try:
        response = await session.get(url=url, headers=headers, proxy=proxy, timeout=TIME_OUT)
        text = await response.text()
        page_body = html.fromstring(text)
        form_hash = str(page_body.xpath('//input[@name=\'formhash\']/@value')[0])
        login_hash = str(page_body.xpath('//form[@name=\'login\']/@action')[0])
        # 调用接口获取js
        js = await get_code_js(session)
        # 分析js获取验证码地址
        pic_url = 'https://obsolete.lightnovel.us/' + \
                  re.findall(".*%s(.*)%s.*" % ('height="30" src="', '" class="vm"'), js)[0]
        pic_res = await http_get_pic(pic_url, session,
                                     'https://obsolete.lightnovel.us/member.php?mod=logging&action=login')
        if pic_res:
            # 图片写入
            pic_path = SAVE_DIR + 'code.jpg'
            write_byte_data(pic_path, pic_res)
    except Exception as e:
        print('获取验证码失败！')
        raise e
    return {'form_hash': form_hash, 'login_hash': login_hash}


async def get_code_js(session):
    # 请求头
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'User-Agent': USER_AGENT,
        'Referer': 'https://obsolete.lightnovel.us/member.php?mod=logging&action=login'
    }
    # 代理
    proxy = PROXIES_URL if PROXIES_URL else None
    # 随机数
    randon_num = random.random()
    url = 'https://obsolete.lightnovel.us/misc.php?mod=seccode&action=update&idhash=cS&%s&modid=undefined' % str(
        randon_num)
    try:
        response = await session.get(url=url, headers=headers, proxy=proxy, timeout=TIME_OUT)
        text = await response.text()
    except Exception as e:
        print('获取验证码失败！')
        raise e
    return text
