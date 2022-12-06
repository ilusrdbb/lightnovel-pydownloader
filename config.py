#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time : 2022/11/18 13:07
# @Author : chaocai

# 保存目录
SAVE_DIR = './books/'
# 抓取站点 masiro 真白萌，esj esj，oldlightnovel 轻国旧站，oldmasiro 真白萌旧站，lightnovel 轻国新站
DEFULT_SITE = 'masiro'
# 最大线程数 不要设置的过大 小心被ban
MAX_THREAD = 10
# 轻国花轻币或真白萌花金币购买 因为手里的号都大几万的金币没测试金币不够的情况 注意剩余金币
IS_PURCHASE = True
# 花费上限，花费高于此值的帖子不花费，请根据自身账号情况修改
MAX_PURCHASE = 101
# 当章节内容少于两张图片时 字数小于此值的章节不抓取 0无限制 轻国旧站建议设置的大一点其余站可以设置的小一些
LEAST_WORDS = 100
# 是否需要登录 有的网站比如真白萌只允许登录查看 请确保自己账号的权限充足
REQUIRED_LOGIN = True
# 登录信息 user 账户名 password 密码
# 注意轻国登录需要验证码，会把验证码保存至SAVE_DIR/code.jpg 然后从控制台输入验证码
LOGIN_INFO = {
    'username': '',
    'password': ''
}
# 连接失败的重试次数
RETRY_TIME = 3
# 下载超时时间
TIME_OUT = 10
# 防ban手段 比如设置2则每次抓章节前睡随机0~2秒 设置0不生效
SLEEP_TIME = 1
# 代理地址 eg http://127.0.0.1:1081 不支持https代理 注意esj只能挂非中日韩节点的代理
PROXIES_URL = ''
# 白名单，轻国不支持该模式
WHITE_LIST = []
# 黑名单，轻国不支持该模式
BLACK_LIST = []
# 开始页
START_PAGE = 1
# 结束页
MAX_PAGE = 1
# 是否总是更新封面和描述信息
ALWAYS_UPDATE_COVER = False
# 是否总是更新章节内容 比如轻国的一些小说在一楼更新就需要打开
ALWAYS_UPDATE_CHAPTER = False
# 轻国屏蔽aid，比如置顶公告
BLACK_AID_LIST = [1113228, 969547, 1099310, 1048596]
# 旧真白萌大板块id，全量抓取会循环板块抓取 [36, 316, 321, 317, 162, 324, 164, 165]
OLD_MASIRO_FIDS = [36, 316, 321, 317, 162, 324, 164, 165]
# 地址配置
URL_CONFIG = {
    'masiro_page': 'https://masiro.me/admin/loadMoreNovels?ori=0&page=%d',
    'masiro_book': 'https://masiro.me%s',
    'masiro_cover': 'https://masiro.me%s',
    'masiro_content': 'https://masiro.me%s',
    'masiro_illustration': '%s',
    'masiro_login': 'https://masiro.me/admin/auth/login',
    'masiro_pay': 'https://masiro.me/admin/pay',
    'esj_page': 'https://www.esjzone.cc/list-11/%d.html',
    'esj_book': 'https://www.esjzone.cc%s',
    'esj_cover': '%s',
    'esj_content': '%s',
    'esj_illustration': '%s',
    'esj_login': 'https://www.esjzone.cc/inc/mem_login.php',
    'oldlightnovel_page': 'https://obsolete.lightnovel.us/forum-173-%d.html',
    'oldlightnovel_book': 'https://obsolete.lightnovel.us/%s',
    'oldlightnovel_chapter': '%s&page=%s',
    'oldlightnovel_illustration': 'https://obsolete.lightnovel.us/%s',
    'oldlightnovel_js': 'https://obsolete.lightnovel.us/misc.php?mod=seccode&action=update&idhash=cS&%s&modid=undefined',
    'oldlightnovel_varify': 'https://obsolete.lightnovel.us/member.php?mod=logging&action=login',
    'oldlightnovel_login': 'https://obsolete.lightnovel.us/%s&inajax=1',
    'oldmasiro_page': 'https://masiro.moe/forum.php?mod=forumdisplay&fid=%d',
    'oldmasiro_book': '%s',
    'oldmasiro_login': 'https://masiro.moe/member.php?mod=logging&action=login&loginsubmit=yes&infloat=yes&lssubmit=yes',
    'oldmasiro_pay': 'https://masiro.moe/forum.php?mod=misc&action=pay&paysubmit=yes&infloat=yes&inajax=1',
    'lightnovel_login': 'https://www.lightnovel.us/proxy/api/user/login',
    'lightnovel_page': 'https://www.lightnovel.us/proxy/api/category/get-article-by-cate',
    'lightnovel_chapter': 'https://www.lightnovel.us/cn/detail/%d',
    'lightnovel_book': 'https://www.lightnovel.us/cn/series/%d',
    'lightnovel_pay': 'https://www.lightnovel.us/proxy/api/coin/use',
}
# xpath
XPATH_DICT = {
    'masiro_page': '//div[@class=\'layui-card\']/a[1]/@href',
    'masiro_cover': '//img[@class=\'img img-thumbnail\']/@src',
    'masiro_title': '//div[@class=\'novel-title\']/text()',
    'masiro_describe': '//div[@class=\'brief\']//text()',
    'masiro_chapter': '//ul[@class=\'episode-ul\']/a',
    'masiro_chapter_name': '//li/span[1]/text()',
    'masiro_chapter_url': '//a/@href',
    'masiro_content': '//div[@class=\'box-body nvl-content\']/p//text()',
    'masiro_illustration': '//div[@class=\'box-body nvl-content\']//img/@src',
    'esj_page': '//a[@class=\'card-img-tiles\']/@href',
    'esj_cover': '//div[contains(@class,\'product-gallery\')]/a/@href',
    'esj_title': '//div[contains(@class,\'book-detail\')]//h2/text()',
    'esj_describe': '//div[@class=\'description\']//text()',
    'esj_chapter': '//div[@id=\'chapterList\']/a',
    'esj_chapter_name': '//p//text()',
    'esj_chapter_url': '//a/@href',
    'esj_content': '//div[contains(@class,\'forum-content\')]/p//text()',
    'esj_illustration': '//div[contains(@class,\'forum-content\')]//img/@src',
    'oldlightnovel_page': '//tbody[contains(@id,\'normalthread_\')]//a[contains(@class,\'xst\')]/@href',
    'oldlightnovel_follow': '//a[@rel=\'nofollow\']/@href',
    'oldlightnovel_title': '//span[@id=\'thread_subject\']/text()',
    'oldlightnovel_num': '//div[@class=\'pg\']//span/@title',
    'oldlightnovel_chapter': '//td[@class=\'t_f\']',
    'oldlightnovel_content': '//text()',
    'oldlightnovel_illustration': '//img/@file',
    'oldlightnovel_formhash': '//input[@name=\'formhash\']/@value',
    'oldlightnovel_loginhash': '//form[@name=\'login\']/@action',
    'tieba_content': '//div[contains(@id,\'post_content_\')]//text()',
    'oldmasiro_page': '//td[@class=\'fl_g\']/dl/dt[1]/a/@href',
    'oldmasiro_title': '//h1[@class=\'xs2\']/a/text()',
    'oldmasiro_num': '//div[@class=\'pg\']//span/@title',
    'oldmasiro_chapter': '//tbody[contains(@id,\'normalthread_\')]',
    'oldmasiro_chapter_name': '//a[contains(@class,\'xst\')]/text()',
    'oldmasiro_chapter_url': '//a[contains(@class,\'xst\')]/@href',
    'oldmasiro_follow': '//a[@rel=\'nofollow\']/@href',
    'oldmasiro_content': '//td[@class=\'t_f\']//text()',
    'oldmasiro_formhash': '//input[@name=\'formhash\']/@value',
    'lightnovel_content': '//article[@id=\'article-main-contents\']//text()',
    'lightnovel_illustration': '//article[@id=\'article-main-contents\']//img/@src',
}
# 通用请求头 一般不需要动
HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36'
}