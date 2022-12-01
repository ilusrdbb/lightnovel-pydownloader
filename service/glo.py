#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time : 2022/11/18 13:05
# @Author : chaocai


def _init():
    global _global_dict
    _global_dict = {}


def set_value(key, value):
    _global_dict[key] = value


def get_value(key, defValue=None):
    try:
        return _global_dict[key]
    except KeyError:
        return defValue