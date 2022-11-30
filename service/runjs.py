import execjs

"""
旧轻国密码加密

:param password: 密码

:return md5
"""


async def js_md5(password):
    with open('./js/md5.js', encoding='utf-8') as f:
        read = f.read()
    js = execjs.compile(read)
    return js.call('hex_md5', password)
