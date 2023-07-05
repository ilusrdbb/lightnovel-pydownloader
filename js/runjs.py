#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time : 2022/11/30
# @Author : chaocai
import subprocess
from functools import partial

from js.dsign import js_dsign

subprocess.Popen = partial(subprocess.Popen, encoding='utf-8')

import execjs


def js_md5(password):
    with open('./js/md5.js', encoding='utf-8') as f:
        read = f.read()
    js = execjs.compile(read)
    return js.call('hex_md5', password)


def get_dsign(read):
    result = None
    try:
        read_cache = read
        read = js_dsign(read)
        js = execjs.compile(read)
        result = js.eval('tempfunction')
        result = result.replace('forrum', 'forum')
    except Exception as e:
        print(read_cache)
        print(read)
        print(e)
    return result
