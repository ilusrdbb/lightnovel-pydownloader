#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time : 2022/11/30 09:00
# @Author : chaocai

import re

async def js_dsign(js):
    js = js[31:-9]
    for st in ['window', 'location', "'assign'", "'href'", "'replace'"]:
        # 找到变量赋值等式
        equal = re.findall('[_A-Za-z0-9 =]+%s;' % st, js)
        # 有可能没有
        if not equal:
            continue
        else:
            equal = equal[0]
        # 找出变量名
        var = equal.split('=')[0].strip()
        # 把等式干掉
        js = js.replace(equal, '')
        # 把变量替换成它真正的意思
        js = js.replace(var, st)
        # 把['xx'] 替换成 .xx
        js = js.replace("['%s']" % st.strip("'"), '.%s' % st.strip("'"))
    js = js.replace('window.href', 'aaaaa')
    js = js.replace('location.assign', 'bbbbb=')
    js = js.replace('location.href', 'bbbbb=')
    js = js.replace('location.replace', 'bbbbb=')
    js = js.replace('location', 'bbbbb=')
    js = js.replace('bbbbb==', 'bbbbb=')
    js = js.replace('for', 'forr')
    return js
