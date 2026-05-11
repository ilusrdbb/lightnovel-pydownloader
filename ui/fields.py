from src.core.constants import SITES

LOGIN_SITE_FIELDS = {
    'esj':    ['username', 'password', 'cookie'],
    'masiro': ['username', 'password', 'cookie'],
    'lk':     ['username', 'password'],
    'yuri':   ['cookie'],
    'fish':   ['username', 'password'],
    'hameln': ['cookie'],
}

CONFIG_FIELDS = [
    ('field', 'sites', '站点', 'multiselect', {
        'options': SITES,
        'tooltip': '配置需要爬取的站点，支持多选',
    }),
    ('field', 'white_list', '白名单', 'text_list', {
        'tooltip': '只爬取白名单内的书籍，每行一个书籍地址或ID',
    }),

    ('login_info', 'login_info', '', '', {}),

    ('field', 'start_page', '开始页', 'int', {
        'default': 1, 'tooltip': '爬取起始页',
    }),
    ('field', 'end_page', '结束页', 'int', {
        'default': 1, 'tooltip': '爬取结束页，不建议一次抓取过多',
    }),
    ('field', 'proxy_url', '代理地址', 'str', {
        'tooltip': '仅支持http代理，例 http://127.0.0.1:1081',
    }),
    ('field', 'is_purchase', '购买章节', 'bool', {
        'default': False, 'tooltip': '轻国或真白萌是否花费金币购买章节',
    }),
    ('field', 'max_purchase', '花费上限', 'int', {
        'default': 20, 'tooltip': '章节花费上限，高于配置值的章节不购买',
    }),
    ('field', 'convert_hans', '繁转简', 'bool', {
        'default': False, 'tooltip': '是否全局繁转简',
    }),

    ('scheduler', 'scheduler_config', '', '', {}),
]

ADVANCE_FIELDS = [
    ('field', 'log_level', '日志级别', 'select', {
        'options': ['INFO', 'DEBUG'], 'default': 'INFO',
        'tooltip': 'INFO 默认 / DEBUG 完整日志',
    }),
    ('field', 'black_list', '黑名单', 'text_list', {
        'tooltip': '爬取时绕过黑名单内的书籍，每行一个，黑名单优先级低于白名单',
    }),

    ('field', 'max_thread', '线程数', 'int', {
        'default': 1, 'min': 1, 'max': 8,
        'tooltip': '不要设置过大，建议1，真白萌/hameln强制单线程',
    }),
    ('field', 'get_collection', '仅爬取收藏', 'bool', {
        'default': True, 'tooltip': '关闭后会爬取全站，不建议关闭',
    }),
    ('field', 'time_out', '请求超时(秒)', 'int', {
        'default': 15, 'min': 1, 'max': 300,
    }),
    ('field', 'sleep_time', '请求间隔(秒)', 'int', {
        'default': 1, 'tooltip': '每次请求前随机睡0~N秒，0不睡眠，真白萌/hameln强制6秒',
    }),
    ('field', 'least_words', '最少字数', 'int', {
        'default': 0, 'tooltip': '字数小于此值且无图片的章节不生成epub章节，0无限制',
    }),

    ('field', 'convert_txt', '导出TXT', 'bool', {'default': False}),
    ('field', 'convert_txt_chapter', '分章节导出TXT', 'bool', {'default': False}),

    ('calibre', 'push_calibre', '', '', {}),

    ('field', 'sign', '开启签到', 'bool', {
        'tooltip': '仅适配轻国和百合会',
    }),
    ('field', 'download_pic_again', '重下失败图片', 'bool', {
        'tooltip': '重新下载全部之前爬取失败的图片',
    }),
    ('field', 'clear_pic_table', '清空图片表', 'bool', {
        'tooltip': '危险！清空数据库中的图片信息，仅在误删图片目录时开启',
    }),
    ('field', 'export_epub_again', '重新导出EPUB', 'bool', {
        'tooltip': '重新导出全部数据库内数据到epub',
    }),

    ('domain', 'domain', '站点域名', '', {}),
    ('field', 'ua', 'User-Agent', 'str', {}),
    ('field', 'esj_book_pwd', 'ESJ书籍密码', 'text_dict', {
        'tooltip': '格式：书籍或章节ID: 密码，每行一个，整本书籍密码优先级高于章节密码',
    }),

]
