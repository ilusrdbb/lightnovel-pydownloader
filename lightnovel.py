#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time : 2022/11/17 15:34
# @Author : chaocai

import asyncio


import service
from service import config, log


# 加载配置文件
config._init()
# 异步
loop = asyncio.get_event_loop()


if __name__ == '__main__':
    log.init_log()
    service.start(loop)
    log.remove_log()
    input('Press Enter to exit...')
