#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time : 2022/11/30 09:00
# @Author : chaocai
import execjs

from js.dsign import js_dsign


async def js_md5(password):
    with open('./js/md5.js', encoding='utf-8') as f:
        read = f.read()
    js = execjs.compile(read)
    return js.call('hex_md5', password)


async def get_dsign(js):
    read = await js_dsign(js)
    js = execjs.compile(read)
    return js.eval('bbbbb')
