#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time : 2023/5/20
# @Author : chaocai
import aiohttp

from service import login, config, page, book


async def start_build(site):
    jar = aiohttp.CookieJar(unsafe=True)
    conn = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=conn, trust_env=True, cookie_jar=jar) as session:
        # 登录
        if config.read('is_login'):
            login_info = login.Login(site)
            if login_info.site == 'masiro':
                await login.masiro_get_token(login_info, session)
            if login_info.site == 'oldlightnovel':
                await login.oldlightnovel_get_hash(login_info, session)
            await login.login(login_info, session)
        await book.build_book(login_info, config.read('white_list'), session) \
            if config.read('white_list') else await page.get_page(login_info, session)


