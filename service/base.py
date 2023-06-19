#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time : 2023/5/20
# @Author : chaocai
import aiohttp

from service import login, config, page, book


async def start_build(site):
    if site == 'all':
        await _start_build('esj')
        await _start_build('masiro')
        await _start_build('lightnovel')
    else:
        await _start_build(site)


async def _start_build(site):
    jar = aiohttp.CookieJar(unsafe=True)
    conn = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=conn, trust_env=True, cookie_jar=jar) as session:
        # 登录
        if config.read('is_login'):
            login_info = login.Login(site)
            await login.login(login_info, session)
        await book.build_book(login_info, config.read('white_list'), session) \
            if config.read('white_list') else await page.get_page(login_info, session)


