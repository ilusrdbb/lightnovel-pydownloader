#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time : 2023/5/20
# @Author : chaocai
import aiohttp

from service import login, config, page, book, log


async def start_build(site):
    # 百合会有概率登录出验证码，暂不考虑all抓取
    if site == 'all':
        try:
            if config.read('login_info')['esj']['username']:
                await _start_build('esj')
        except Exception:
            pass
        try:
            if config.read('login_info')['lightnovel']['username']:
                await _start_build('lightnovel')
        except Exception:
            pass
        try:
            if config.read('login_info')['masiro']['username']:
                await _start_build('masiro')
        except Exception:
            pass
    else:
        if config.read('login_info')[site]['username']:
            await _start_build(site)


async def _start_build(site):
    if site == 'masiro' and not config.read('flaresolverr_url'):
        log.info('真白萌请自行搭建flaresolverr')
        return
    jar = aiohttp.CookieJar(unsafe=True)
    conn = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=conn, trust_env=True, cookie_jar=jar) as session:
        # 登录
        login_info = login.Login(site)
        await login.login(login_info, session)
        await book.build_book(login_info, config.read('white_list'), session) \
            if config.read('white_list') else await page.get_page(login_info, session)


