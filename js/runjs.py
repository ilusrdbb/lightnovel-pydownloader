#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time : 2022/11/30 09:00
# @Author : chaocai

import subprocess
from functools import partial
subprocess.Popen = partial(subprocess.Popen, encoding='utf-8')

import execjs

from js.dsign import js_dsign


async def js_md5(password):
    with open('./js/md5.js', encoding='utf-8') as f:
        read = f.read()
    js = execjs.compile(read)
    return js.call('hex_md5', password)


async def get_dsign(read):
    read = await js_dsign(read)
    js = execjs.compile(read)
    return js.eval('bbbbb')


async def get_series(read):
    read = read.replace('window.__NUXT__', 'ccccc')
    js = execjs.compile(read)
    return js.eval('ccccc')
