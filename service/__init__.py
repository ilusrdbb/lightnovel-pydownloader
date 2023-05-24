#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time : 2022/11/18 13:00
# @Author : chaocai
from __future__ import annotations

import asyncio

import service.base
from service import config


def start():
    # 加载配置文件
    config._init()
    # 异步
    loop = asyncio.get_event_loop()
    loop.run_until_complete(service.base.start_build(config.read('site')))
