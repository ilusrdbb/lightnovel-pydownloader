#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time : 2022/11/18 13:00
# @Author : chaocai
from __future__ import annotations

import service.base
from service import config


def start(loop):
    loop.run_until_complete(service.base.start_build(config.read('site')))
