#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time : 2023/5/20
# @Author : chaocai
import json
import random

from lxml import html

from js.runjs import js_md5
from service import config, util, log


class Login:
    # 站点
    site: None
    # 地址
    url: None
    # 用户名
    username: None
    # 密码
    password: None
    # token 真白萌、轻国需要
    token: None
    # hash 百合会需要
    hash: None
    # 轻国uid
    uid: None
    # 真白萌ua
    ua: None
    # 真白萌cf cookie
    cf: None

    # 初始化
    def __init__(self, site):
        self.site = site
        self.url = config.read('url_config')[site]['login']
        self.username = config.read('login_info')[site]['username']
        self.password = config.read('login_info')[site]['password']


# discuz论坛获取hash以及验证码
async def discuz_get_hash(login_info, session):
    # 获取hash
    headers = config.read('headers')
    res = await util.http_get(config.read('url_config')[login_info.site]['hash'], headers,
                              None, '获取登录hash失败！', session)
    page_body = html.fromstring(res)
    login_info.hash = {'formhash': str(page_body.xpath('//input[@name=\'formhash\']/@value')[0]),
                       'loginhash': str(page_body.xpath('//form[@name=\'login\']/@action')[0])}
    # 调用接口获取js 这段代码作废 留存用作登录出验证码的处理
    if login_info.site == 'oldlightnovel':
        log.info('开始获取验证码...')
        headers['Referer'] = config.read('url_config')[login_info.site]['hash']
        js_text = await util.http_get(
            'https://obsolete.lightnovel.us/misc.php?mod=seccode&action=update&idhash=cS&%s&modid=undefined' % str(
                random.random()),
            headers, None, '获取验证码失败！', session)
        # 分析js获取验证码地址
        headers['Accept'] = 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8'
        pic_res = await util.http_get_pic(
            'https://obsolete.lightnovel.us/%s' % util.get_split_str_list('height="30" src="', '" class="vm"', js_text)[
                0],
            headers, session)
        pic_path = config.read('txt_dir') + 'code.jpg'
        util.write_byte_data(config.read('txt_dir') + 'code.jpg', pic_res)
        log.info('已获取验证码，图片存放位置%s' % pic_path)


# 真白萌获取token
async def masiro_get_token(login_info, session):
    log.info('真白萌开始破盾...')
    flaresolverr_res = await util.http_flaresolverr_post(config.read('flaresolverr_url'), 'https://masiro.me/admin/wishingPondIndex',
                                                         'cf破盾失败，重试中...', session)
    login_info.ua = flaresolverr_res['userAgent']
    login_info.cf = flaresolverr_res['cookies'][0]['value']
    headers = {
        'referer': 'https://masiro.me/admin',
        'user-agent': login_info.ua,
        'cookie': 'cf_clearance=' + login_info.cf
    }
    res = await util.http_get('https://masiro.me/admin/auth/login', headers, None, '获取token失败！', session)
    page_body = html.fromstring(res)
    login_info.token = str(page_body.xpath('//input[@class=\'csrf\']/@value')[0])


# 登录入口
async def login(login_info, session):
    if login_info.site == 'masiro':
        # 真白萌设置token
        await masiro_get_token(login_info, session)
    if login_info.site == 'yuri':
        # discuz获取hash
        await discuz_get_hash(login_info, session)
    login_param = build_login_param(login_info)
    login_headers = build_login_headers(login_info)
    if login_info.site == 'yuri':
        login_info.url = login_info.url % login_info.hash['loginhash']
    res = await util.http_post(login_info.url, login_headers, login_param, None, '登录失败！',
                               True if login_info.site == 'lightnovel' else False, session)
    if '验证码填写错误' in res:
        raise Exception('验证码填写错误！')
    if login_info.site == 'lightnovel':
        # 轻国设置token和uid
        login_info.token = json.loads(res)['data']['security_key']
        login_info.uid = json.loads(res)['data']['uid']
    log.info('登录成功！')


# 构造请求头
def build_login_headers(login_info):
    headers = config.read('headers')
    if login_info.site == 'masiro':
        headers['origin'] = 'https://masiro.me'
        headers['referer'] = 'https://masiro.me/admin'
        headers['user-agent'] = login_info.ua
        headers['x-csrf-token'] = login_info.token
        headers['cookie'] = 'cf_clearance=' + login_info.cf
    if login_info.site == 'lightnovel':
        headers['Accept'] = 'application/json, text/plain, */*'
        headers['Accept-Language'] = 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7'
        headers['Origin'] = 'https://www.lightnovel.us'
        headers['Referer'] = 'https://www.lightnovel.us/cn/'
    return headers


# 构造传参
def build_login_param(login_info):
    if login_info.site == 'masiro':
        return {
            'username': login_info.username,
            'password': login_info.password,
            'remember': '1',
            '_token': login_info.token
        }
    if login_info.site == 'esj':
        return {
            'email': login_info.username,
            'pwd': login_info.password,
            'remember_me': 'on'
        }
    if login_info.site == 'oldlightnovel':
        # 输入验证码
        print('请输入验证码：')
        code = input()
        return {
            'formhash': login_info.hash['formhash'],
            'referer': 'https://obsolete.lightnovel.us/thread-1029685-1-1.html',
            'username': login_info.username,
            'password': js_md5(login_info.password),
            'questionid': '0',
            'answer': '',
            'seccodehash': 'cS',
            'seccodemodid': 'member::logging',
            'cookietime': '2592000',
            'seccodeverify': code
        }
    if login_info.site == 'yuri':
        return {
            'formhash': login_info.hash['formhash'],
            'referer': 'https://bbs.yamibo.com/forum-55-2.html',
            'username': login_info.username,
            'password': login_info.password,
            'questionid': '0',
            'answer': '',
            'cookietime': '2592000'
        }
    if login_info.site == 'lightnovel':
        return {
            'client': 'web',
            'd': {
                'username': login_info.username,
                'password': login_info.password,
            },
            'gz': 0,
            'is_encrypted': 0,
            'platform': 'pc',
            'sign': ''
        }
