#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time : 2022/12/09 10:00
# @Author : chaocai

import os

if __name__ == '__main__':
    """
    合并txt的粗糙小工具，做epub啥的建议用现成的轮子
    """
    book_path = '../books/lightnovel/[とまとすぱげてぃ][web]转生成夹在百合中间的男人了 第六章 你觉得你在百合游戏世界里还能说出同样的话吗？③_3195_'
    book_name = book_path.split('/')[-1]
    out_path = '../books/' + book_name + '.txt'
    file_list = os.listdir(book_path)
    # 创建时间正序排序
    new_file_list = sorted(file_list, key=lambda file: os.path.getctime(os.path.join(book_path, file)))
    # 合并
    with open(out_path, 'w', encoding='utf-8') as f:
        for filename in new_file_list:
            filepath = book_path + '/' + filename
            with open(filepath, encoding='utf-8') as ff:
                txt = ff.read()
                f.write(txt)
            f.write('\n')
            f.write('-------------------------------------------')
            f.write('\n')
