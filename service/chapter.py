#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time : 2023/5/20
# @Author : chaocai
import asyncio
import base64
import json
import os
import random
import re

from lxml import html
from zhconv import zhconv

from service import config, util, log


class Chapter:
    # id
    id: None
    # 地址
    url: None
    # 标题
    title: None
    # 内容
    content: None
    # 顺序
    order: None
    # 图片地址或路径
    pic: None

    # 初始化
    def __init__(self, id, url, title, content, order, pic):
        self.id = id
        self.url = url
        self.title = title
        self.content = content
        self.order = order
        self.pic = pic


# 前置工作，主要是更新文件顺序号
async def build_chapter(login_info, book_data, chapter_data, session):
    always_update = config.read('always_update')
    if login_info.site != 'lightnovel':
        chapter_data.id = get_chapter_id(login_info, chapter_data.url)
    elif login_info.site == 'lightnovel' and book_data.sid == 0:
        # 总是更新轻国的单独章节书籍
        always_update = True
    if chapter_data.id:
        chapter_data.pic = []
        chapter_data.content = []
        # 获取书籍目录下带id的文本和插图路径
        old_paths = util.find_id_path(book_data.path, chapter_data.id)
        old_txt_path = None
        if old_paths:
            old_txt_path = [item for item in old_paths if '.txt' in item]
        if old_txt_path and not always_update:
            old_txt_path = old_txt_path[0]
            # 填入标题和内容，不需要重新抓取
            chapter_data.title = old_txt_path.split('_')[3]
            with open(old_txt_path, encoding='utf-8') as f:
                chapter_data.content = [f.read()]
            if not old_txt_path.startswith('#' + str(chapter_data.order) + '_'):
                # 新旧顺序号不同，重命名
                for old_path in old_paths:
                    old_order = '#' + re.search(r'#(\d+)_', old_path).group(1)
                    new_path = old_path.replace(old_order, '#' + str(chapter_data.order))
                    os.rename(old_path, new_path)
                    # 刷新图片地址list
                    if '.txt' not in new_path:
                        chapter_data.pic.append(new_path)
            else:
                # 新旧顺序号相同，填入图片地址list
                chapter_data.pic = [item for item in old_paths if '.txt' not in item]
            return
        elif old_txt_path and always_update:
            # 删除旧路径文件，重新抓取
            for old_path in old_paths:
                if os.path.isfile(old_path):
                    os.remove(old_path)
    if config.read('sleep_time') > 0:
        await asyncio.sleep(random.random() * config.read('sleep_time'))
    if login_info.site != 'lightnovel':
        await _build_chapter(login_info, book_data, chapter_data, session)
    else:
        await lightnovel_build_chapter(login_info, book_data, chapter_data, session)


# 轻国抓取章节内容
async def lightnovel_build_chapter(login_info, book_data, chapter_data, session):
    page_url = 'https://api.lightnovel.us/api/article/get-detail'
    param_str = '{"platform":"android","client":"app","sign":"","ver_name":"0.11.50","ver_code":190,' \
                '"d":{"aid":' + chapter_data.id + ',"simple":0,"security_key":"' + login_info.token + '"},"gz":1}'
    text = await util.http_post(page_url, util.build_headers(login_info), json.loads(param_str),
                                '%s已获取章节 %s' % (book_data.title, chapter_data.title),
                                '%s章节连接已断开，重试中... %s' % (book_data.title, chapter_data.title), True, session)
    if util.unzip(text).get('data'):
        text_data = util.unzip(text)['data']
        # 轻国打钱
        if text_data.get('pay_info'):
            if text_data.get('pay_info')['is_paid'] == 0 and config.read('is_purchase'):
                cost = text_data.get('pay_info')['price']
                if cost > config.read('max_purchase'):
                    text_data = await lightnovel_pay(login_info, cost, book_data, chapter_data, text_data, session)
        # 正则从文本里提取插图
        pic_pattern = r'\[img\](.*?)\[/img\]'
        chapter_data.pic = re.findall(pic_pattern, text_data['content'])
        # 文本中剔除插图
        pic_pattern = r'\[img\].*?\[/img\]'
        no_img_content = re.sub(pic_pattern, '', text_data['content'])
        # 从bbcode里提取文字
        chapter_data.content = [re.sub(r'\[.*?\]', '', no_img_content)]
        # 写入文本
        content_path = book_data.path + '/#' + str(chapter_data.order) + '_' + \
                       chapter_data.title + '_' + chapter_data.id + '_' + '.txt'
        util.write_str_data(content_path, '\n'.join(chapter_data.content))
        # 写入图片
        if chapter_data.pic and config.read('get_pic'):
            await download_pic(login_info, book_data, chapter_data, session)


# 轻国打钱
async def lightnovel_pay(login_info, cost, book_data, chapter_data, text_data, session):
    log.info('%s开始打钱..花费:%s' % (book_data.title, str(cost)))
    cost_url = 'https://api.lightnovel.us/api/coin/use'
    cost_param = '{"platform":"android","client":"app","sign":"","ver_name":"0.11.50","ver_code":190,' \
                 '"d":{"goods_id":1,"params":' + chapter_data.id + ',"price":' + str(cost) + \
                 ',"number":1,"totla_price":' + str(cost) + ',' \
                                                            '"security_key":"' + login_info.token + '"},"gz":1}'
    cost_res = await util.http_post(cost_url, util.build_headers(login_info), json.loads(cost_param), None,
                                    '%s打钱失败... %s' % (book_data.title, chapter_data.title), True, session)
    if util.unzip(cost_res)['code'] == 0:
        # 刷新章节内容
        page_url = 'https://api.lightnovel.us/api/article/get-detail'
        param_str = '{"platform":"android","client":"app","sign":"","ver_name":"0.11.50","ver_code":190,' \
                    '"d":{"aid":' + chapter_data.id + ',"simple":0,"security_key":"' + login_info.token + '"},"gz":1}'
        text = await util.http_post(page_url, util.build_headers(login_info), json.loads(param_str), None,
                                    '%s章节连接已断开，重试中... %s' % (book_data.title, chapter_data.title), True, session)
        return util.unzip(text)['data']
    else:
        return text_data


# 构造章节标题、图片、内容
async def _set_chapter(login_info, book_data, chapter_data, session):
    # esj不考虑外链
    if login_info.site == 'esj' and 'esjzone.cc' not in chapter_data.url:
        chapter_data.content = [chapter_data.url]
        chapter_data.title = 'esj外链，地址见文本内容'
        return
    text = await util.http_get(chapter_data.url, util.build_headers(login_info),
                               '%s已获取章节 地址：%s' % (book_data.title, chapter_data.url),
                               '章节连接已断开，重试中... %s' % chapter_data.url, session)
    page_body = html.fromstring(text)
    chapter_data.content = page_body.xpath(config.read('xpath_config')[login_info.site]['content'])
    chapter_data.pic = page_body.xpath(config.read('xpath_config')[login_info.site]['pic'])
    try:
        chapter_data.title = page_body.xpath(config.read('xpath_config')[login_info.site]['chapter_title'])[0]
        if len(chapter_data.title) > 70:
            chapter_data.title = chapter_data.title[:70]
    except:
        chapter_data.title = None
    # 打钱
    await chapter_purchase(login_info, book_data, chapter_data, page_body, session)


# 打钱
async def chapter_purchase(login_info, book_data, chapter_data, page_body, session):
    if login_info.site == 'masiro':
        if not chapter_data.title and config.read('is_purchase'):
            cost = int(page_body.xpath('//input[@class=\'cost\']/@value')[0])
            if cost <= config.read('max_purchase'):
                log.info('%s开始打钱..花费:%s' % (book_data.title, str(cost)))
                res = await util.http_post('https://masiro.me/admin/pay', util.build_headers(login_info, False, True),
                                           {'type': '2', 'object_id': chapter_data.id, 'cost': cost}, None,
                                           '%s %s 打钱失败！' % (book_data.title, chapter_data.id), False, session)
                if res and json.loads(res)['code'] == 1:
                    text = await util.http_get(chapter_data.url, util.build_headers(login_info), None,
                                               '章节连接已断开，重试中... %s' % chapter_data.url, session)
                    page_body = html.fromstring(text)
                    chapter_data.content = page_body.xpath(config.read('xpath_config')[login_info.site]['content'])
                    chapter_data.pic = page_body.xpath(config.read('xpath_config')[login_info.site]['pic'])
                    chapter_data.title = page_body.xpath(config.read('xpath_config')[login_info.site]['chapter_title'])[0]


# 写入章节信息
async def _build_chapter(login_info, book_data, chapter_data, session):
    await _set_chapter(login_info, book_data, chapter_data, session)
    if not chapter_data.title:
        return
    # 写入文本
    chapter_data.title = zhconv.convert(chapter_data.title, 'zh-hans') \
        if config.read('convert_hans') else chapter_data.title
    chapter_data.title = util.format_text(chapter_data.title)
    content_path = book_data.path + '/#' + str(chapter_data.order) + '_' + \
                   chapter_data.title + '_' + chapter_data.id + '_' + '.txt'
    util.write_str_data(content_path, '\n'.join(chapter_data.content))
    # 写入图片
    if chapter_data.pic and config.read('get_pic'):
        await download_pic(login_info, book_data, chapter_data, session)


# 旧轻国抓取页面
async def build_oldlightnovel_chapter(login_info, book_data, session):
    # 只看楼主
    book_data.url = 'https://obsolete.lightnovel.us/forum.php?mod=viewthread&tid=%s&page=1&authorid=%s' \
                    % (book_data.id, book_data.author_id)
    text = await util.http_get(book_data.url, util.build_headers(login_info),
                               '%s已获取书籍 地址：%s' % (book_data.title, book_data.url),
                               '书籍连接已断开，重试中... %s' % book_data.url, session)
    page_body = html.fromstring(text)
    await oldlightnovel_set_chapter(login_info, page_body, book_data, session)
    # 获取页数
    pages = page_body.xpath('//div[@class=\'pg\']//span/@title')
    if pages:
        page_num = int(re.findall('\d+', pages[0])[0])
        if page_num > 1:
            for num in range(2, page_num + 1):
                page_url = 'https://obsolete.lightnovel.us/forum.php?mod=viewthread&tid=%s&page=%s&authorid=%s' \
                           % (book_data.id, str(num), book_data.author_id)
                text = await util.http_get(page_url, util.build_headers(login_info), None,
                                           '书籍连接已断开，重试中... %s' % book_data.url, session)
                page_body = html.fromstring(text)
                await oldlightnovel_set_chapter(login_info, page_body, book_data, session)


# 旧轻国获取章节
async def oldlightnovel_set_chapter(login_info, page_body, book_data, session):
    max_order = book_data.max_order
    text_list = page_body.xpath('//td[@class=\'t_f\']')
    for text in text_list:
        max_order += 1
        body = html.fromstring(html.tostring(text))
        content = body.xpath('//text()')
        pic_url_list = body.xpath('//img/@file')
        chapter_data = Chapter(str(max_order), None, str(max_order), content, max_order, pic_url_list)
        # 写入文本
        content_path = book_data.path + '/#' + str(chapter_data.order) + '_' + \
                       chapter_data.title + '_' + chapter_data.id + '.txt'
        util.write_str_data(content_path, '\n'.join(chapter_data.content))
        # 写入图片
        if chapter_data.pic and config.read('get_pic'):
            await download_pic(login_info, book_data, chapter_data, session)
        book_data.max_order = max_order
        book_data.chapter.append(chapter_data)


# 下载插图
async def download_pic(login_info, book_data, chapter_data, session):
    pics = chapter_data.pic
    pics_path = []
    pic_count = 1
    for pic_url in pics:
        if pic_url.startswith('data:image'):
            # 直接写流
            pic_name = str(pic_count) + '.jpeg'
            pic = base64.urlsafe_b64decode(pic_url.split(',')[1])
            if config.read('least_pic') > 0 and len(pic) < config.read('least_pic'):
                continue
            path = book_data.path + '/#' + str(chapter_data.order) + '_' + chapter_data.id + '_' + pic_name
            util.write_byte_data(path, pic)
            pics_path.append(path)
            pic_count += 1
            continue
        if 'noire.cc:233' in pic_url:
            pic_url = pic_url.replace('noire.cc:233', 'noire.cc')
        if 'i.noire.cc:332' in pic_url:
            pic_url = pic_url.replace('i.noire.cc:332', 'i.noire.cc')
        if not pic_url.startswith('http'):
            pic_url = config.read('url_config')[login_info.site]['pic'] % pic_url
        pic_name = format_pic_name(pic_url)
        if login_info.site == 'oldlightnovel':
            pic_name = str(pic_count) + '.jpg'
        if pic_name.endswith('.i'):
            pic_name = pic_name.replace('.i', '.avif')
        path = book_data.path + '/#' + str(chapter_data.order) + '_' + chapter_data.id + '_' + pic_name
        pic = await util.http_get_pic(pic_url, util.build_headers(login_info, True, False), session,
                                      book_data.title + '_' + chapter_data.title)
        if pic:
            if config.read('least_pic') > 0 and len(pic) < config.read('least_pic'):
                continue
            util.write_byte_data(path, pic)
            if pic_name.endswith('.avif'):
                # 轻国avif转png
                path = util.convert_avif_png(path)
            pics_path.append(path)
            pic_count += 1
    chapter_data.pic = pics_path


# 插图文件名规范
def format_pic_name(pic_url):
    pic_name = pic_url.split('/')[-1].replace(':', '').replace('*', '')
    if '?' in pic_name:
        pic_name = pic_name.replace('?' + pic_url.split('?')[-1], '')
    pic_name = pic_name.replace('?', '').replace('_', '')
    if len(pic_name) > 100:
        pic_name = pic_name[0:100]
    return pic_name


# 获取章节id
def get_chapter_id(login_info, chapter_url):
    if login_info.site == 'esj':
        try:
            return re.search(r'/(\d+)\.html', chapter_url).group(1)
        except:
            return chapter_url.split('/')[-1]
    if login_info.site == 'masiro':
        return chapter_url.split('?cid=')[-1]
