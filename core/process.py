import aiohttp

from core.reload import Reload
from sites.esj import Esj
from sites.lk import Lk
from sites.masiro import Masiro
from sqlite.database import Database
from utils import config, log


class Process(object):
    site: str

    def __init__(self, site: str):
        self.site = site

    async def run(self):
        if not config.read("scheduler_config")["enabled"] and config.read("delete_pic_table"):
            # 删图片库
            with Database() as db:
                db.pic.clear()
            log.info("数据库图片地址信息已清除！")
            return
        if not config.read("scheduler_config")["enabled"] and config.read("download_fail_again"):
            # 重新下载图片
            await Reload().re_download()
            log.info("图片已重新下载！")
            return
        if not config.read("scheduler_config")["enabled"] and config.read("purchase_again"):
            # 重爬打钱章节
            await Reload().re_pay()
            log.info("已重新打钱！")
            return
        sites = [self.site]
        if self.site == "all":
            sites = ["esj", "lk", "masiro"]
        for site in sites:
            jar = aiohttp.CookieJar(unsafe=True)
            conn = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=conn, trust_env=True, cookie_jar=jar) as session:
                if site == "esj":
                    await Esj(session).run()
                if site == "lk":
                    await Lk(session).run()
                if site == "masiro":
                    await Masiro(session).run()
                await session.close()
