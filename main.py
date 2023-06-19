#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time : 2022/11/17 15:34
# @Author : chaocai

import asyncio

from apscheduler.schedulers.blocking import BlockingScheduler

import service
from service import config, log

# 定时执行
sc = BlockingScheduler(timezone='Asia/Shanghai')
# 加载配置文件
config._init()
time_list = config.read('cron_time').split(':')
# 异步
loop = asyncio.get_event_loop()


@sc.scheduled_job('cron', hour=time_list[0], minute=time_list[1], second=time_list[2])
def cron_start():
    log.init_log()
    service.start(loop)
    log.remove_log()


if __name__ == '__main__':
    if config.read('is_cron'):
        try:
            sc.start()
        except Exception as e:
            sc.shutdown()
    else:
        cron_start()
        input('Press Enter to exit...')
