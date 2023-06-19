#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time : 2023/6/7
# @Author : chaocai
import logging
import os
import time


# 初始化log
def init_log():
    today = time.strftime('%Y-%m-%d', time.localtime(time.time()))
    log_path = './log'
    log_name = today + ".log"
    if not os.path.exists(log_path):
        os.makedirs(log_path)
    if not os.path.exists('./log/{}'.format(log_name)):
        report_file = open('./log/{}'.format(log_name), 'w')
        report_file.close()
    global logger
    logger = logging.getLogger()
    handler = logging.FileHandler('./log/{}'.format(log_name), encoding='utf8')
    console = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    console.setFormatter(formatter)
    logger.addHandler(console)


# 移除log handler 防止重复打印
def remove_log():
    logger.removeHandler(logger.handlers[0])
    logger.removeHandler(logger.handlers[0])


# 通用打印方法
def info(message):
    logger.setLevel(logging.INFO)
    logging.info(message)