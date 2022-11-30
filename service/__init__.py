#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time : 2022/11/18 13:00
# @Author : chaocai

from __future__ import annotations

import asyncio


import service.base
from service.config import *

"""
爬虫入口
开始前建议阅读config.py下的配置项
爬取失败的图片会写入至missing.txt中

"""


def start(site_type = DEFULT_SITE):
    loop = asyncio.get_event_loop()
    # 全量
    if not WHITE_LIST:
        loop.run_until_complete(
            service.base.build_all_book(site_type))
    # 白名单
    else:
        loop.run_until_complete(
            service.base.build_some_book(site_type))
