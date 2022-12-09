#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time : 2022/11/30 09:00
# @Author : chaocai

import random

from lxml import html

from js.runjs import js_md5
from service import glo
from service.util import *
from config import *


async def start_login(site_type, session):
    # 真白萌token
    if site_type == 'masiro':
        await masiro_get_token(URL_CONFIG[site_type + '_login'], session)
    # 旧轻国验证码
    if site_type == 'oldlightnovel':
        await oldlightnovel_get_code(URL_CONFIG['oldlightnovel_varify'], session)
    # 登录
    await http_login(site_type, session)


async def masiro_get_token(url, session):
    print('开始获取token...')
    # 代理
    proxy = PROXIES_URL if PROXIES_URL else None
    try:
        response = await session.get(url=url, headers=HEADERS, proxy=proxy, timeout=TIME_OUT)
        if not response.status == 200:
            raise Exception('获取token失败！')
        text = await response.text()
        page_body = html.fromstring(text)
        glo.set_value('gl_masiro_token', str(page_body.xpath('//input[@class=\'csrf\']/@value')[0]))
    except Exception as e:
        print('获取token失败！')
        raise e


async def oldlightnovel_get_code(url, session):
    print('开始获取验证码...')
    # 请求头
    headers = HEADERS
    headers['Referer'] = 'https://obsolete.lightnovel.us/thread-1029685-1-1.html'
    # 代理
    proxy = PROXIES_URL if PROXIES_URL else None
    try:
        response = await session.get(url=url, headers=headers, proxy=proxy, timeout=TIME_OUT)
        text = await response.text()
        page_body = html.fromstring(text)
        # 获取登录时必要的参数hash
        glo.set_value('gl_oldlightnovel_formhash', str(page_body.xpath(XPATH_DICT['oldlightnovel_formhash'])[0]))
        glo.set_value('gl_oldlightnovel_loginhash', str(page_body.xpath(XPATH_DICT['oldlightnovel_loginhash'])[0]))
        # 调用接口获取js
        js = await oldlightnovel_get_js(session)
        # 分析js获取验证码地址
        pic_url = URL_CONFIG['oldlightnovel_book'] % get_split_str_list('height="30" src="', '" class="vm"', js)[0]
        pic_res = await http_get_pic(pic_url, session, URL_CONFIG['oldlightnovel_varify'])
        if pic_res:
            # 图片写入
            pic_path = SAVE_DIR + 'code.jpg'
            write_byte_data(pic_path, pic_res)
            print('已获取验证码，图片存放位置%s' % pic_path)
    except Exception as e:
        print('获取验证码失败！')
        raise e


async def oldlightnovel_get_js(session):
    # 请求头
    headers = HEADERS
    headers['Referer'] = 'https://obsolete.lightnovel.us/member.php?mod=logging&action=login'
    # 代理
    proxy = PROXIES_URL if PROXIES_URL else None
    # 随机数
    randon_num = random.random()
    url = URL_CONFIG['oldlightnovel_js'] % str(randon_num)
    try:
        response = await session.get(url=url, headers=headers, proxy=proxy, timeout=TIME_OUT)
        text = await response.text()
    except Exception as e:
        print('获取验证码失败！')
        raise e
    return text


async def http_login(site_type, session):
    print('开始登录...')
    if site_type == 'oldlightnovel':
        url = URL_CONFIG[site_type + '_login'] % glo.get_value('gl_oldlightnovel_loginhash')
    else:
        url = URL_CONFIG[site_type + '_login']
    # 传参
    param_data = await get_login_param(site_type)
    # 请求头
    headers = await get_login_header(site_type)
    # 代理
    proxy = PROXIES_URL if PROXIES_URL else None
    try:
        if site_type == 'lightnovel':
            response = await session.post(url=url, headers=headers, proxy=proxy, json=param_data, timeout=TIME_OUT)
        else:
            response = await session.post(url=url, headers=headers, proxy=proxy, data=param_data, timeout=TIME_OUT)
        if not response.status == 200:
            raise Exception('登录失败！')
        text = await response.text()
        if '验证码填写错误' in text:
            raise Exception('验证码错误！')
        if site_type == 'lightnovel':
            # 轻国手动设置cookie
            text = json.loads(text)
            glo.set_value('gl_lightnovel_token', text['data']['security_key'])
        print('登录成功！')
    except Exception as e:
        print('登录失败！')
        raise e


async def get_login_param(site_type):
    param_data = {}
    if site_type == 'masiro':
        param_data = {
            'username': LOGIN_INFO['username'],
            'password': LOGIN_INFO['password'],
            'remember': '1',
            '_token': glo.get_value('gl_masiro_token')
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
            'formhash': glo.get_value('gl_oldlightnovel_formhash'),
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
    if site_type == 'lightnovel':
        param_data = {
            'client': 'web',
            'd': {
                'username': LOGIN_INFO['username'],
                'password': LOGIN_INFO['password'],
            },
            'gz': 0,
            'is_encrypted': 0,
            'platform': 'pc',
            'sign': ''
        }
    return param_data


async def get_login_header(site_type):
    headers = HEADERS
    if site_type == 'masiro':
        headers['x-csrf-token'] = glo.get_value('gl_masiro_token')
        headers['x-requested-with'] = 'XMLHttpRequest'
    if site_type == 'lightnovel':
        headers['Accept'] = 'application/json, text/plain, */*'
        headers['Accept-Language'] = 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7'
        headers['Origin'] = 'https://www.lightnovel.us'
        headers['Referer'] = 'https://www.lightnovel.us/cn/'
    return headers
