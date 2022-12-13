#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time : 2022/12/09 10:00
# @Author : chaocai

import os

if __name__ == '__main__':
    """
    合并txt的粗糙小工具，做epub啥的建议用现成的轮子
    """
    book_path = '../books/masiro/TS少女的赎罪~回溯原勇者是勇者小队的女剑士~'
    book_name = book_path.split('/')[-1]
    out_path = '../books/' + book_name + '.txt'
    file_list = os.listdir(book_path)
    # 创建时间正序排序
    new_file_list = sorted(file_list, key=lambda file: os.path.getctime(os.path.join(book_path, file)))
    # 合并
    with open(out_path, 'w', encoding='utf-8') as f:
        for filename in new_file_list:
            if '.txt' in filename:
                filepath = book_path + '/' + filename
                with open(filepath, encoding='utf-8') as ff:
                    txt = ff.read()
                    f.write(txt)
                f.write('\n')
                f.write('-------------------------------------------')
                f.write('\n')
