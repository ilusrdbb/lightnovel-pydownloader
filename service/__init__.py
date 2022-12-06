#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time : 2022/11/18 13:00
# @Author : chaocai

from __future__ import annotations

import asyncio

import service.base
from config import *
from service import glo


def start(site_type = DEFULT_SITE):
    # 全局变量初始化
    glo._init()
    loop = asyncio.get_event_loop()
    # 全量
    if not WHITE_LIST:
        loop.run_until_complete(
            service.base.build_all_book(site_type))
    # 白名单
    else:
        loop.run_until_complete(
            service.base.build_some_book(site_type))
