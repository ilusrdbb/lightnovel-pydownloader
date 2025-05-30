import aiohttp

from src.sites.esj import Esj
from src.sites.lk import LK
from src.sites.masiro import Masiro
from src.sites.yuri import Yuri
from src.utils.config import read_config


class Process(object):

    @staticmethod
    async def run():
        for site in read_config("sites"):
            jar = aiohttp.CookieJar()
            conn = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=conn, cookie_jar=jar) as session:
                if site == "esj":
                    await Esj(session).run()
                if site == "lk":
                    await LK(session).run()
                if site == "masiro":
                    await Masiro(session).run()
                if site == "yuri":
                    await Yuri(session).run()
