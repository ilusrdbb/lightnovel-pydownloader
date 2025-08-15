import asyncio
import json
from typing import List, Dict
from urllib.parse import quote

from aiohttp import ClientSession

from src.db import cookie
from src.db.book import update_book
from src.db.cookie import update_cookie
from src.models.book import Book
from src.models.cookie import Cookie
from src.utils import request
from src.utils.config import read_config
from src.utils.log import log


class Fish:

    def __init__(self, session: ClientSession):
        self.session = session
        self.site: str = "fish"
        self.domain: str = read_config("domain")["fish"]
        self.cookie: Cookie = None
        self.books: List[Book] = []
        # 默认请求头
        self.header: Dict[str, str] = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate, zstd",
            "Accept-Language": "zh-CN,zh;q=0.9,zh-HK;q=0.8,en-US;q=0.7,en;q=0.6",
            "User-Agent": read_config("ua")
        }

    async def run(self):
        try:
            # 校验cookie
            self.cookie = await cookie.get_cookie(self.site)
            if self.cookie and self.cookie.token:
                self.header["Authorization"] = self.cookie.token
            is_effective_cookie = False if not self.cookie else await self.valid_cookie()
            if not is_effective_cookie:
                # 登录
                log.info(f"{self.site}开始登录...")
                await self.login()
                log.info(f"{self.site}登录成功")
            # 获取书籍列表
            await self.get_book_list()
            if not self.books:
                log.info(f"{self.site}未获取到书籍")
                return
            # 下载
            for book in self.books:
                await self.download(book)
        except Exception as e:
            log.info(str(e))

    async def valid_cookie(self) -> bool:
        url = f"{self.domain}/api/user/favored-web/default?page=0&pageSize=30&query=&provider=kakuyomu%2Csyosetu%2Cnovelup%2Chameln%2Cpixiv%2Calphapolis&type=0&level=0&translate=0&sort=update"
        res = await request.get(url, self.header, self.session)
        if res and res.startswith("{"):
            log.info("轻小说机翻站校验cookie成功")
            return True
        log.info("轻小说机翻站cookie失效")
        log.debug(res)
        return False

    async def login(self):
        cookie = Cookie()
        cookie.source = "fish"
        if not read_config("login_info")["fish"]["authorization"]:
            raise Exception("轻小说机翻站未配置登录信息")
        cookie.token = read_config("login_info")["fish"]["authorization"]
        # 再校验一次cookie
        self.cookie = cookie
        self.header["Authorization"] = cookie.token
        is_effective_cookie = await self.valid_cookie()
        if not is_effective_cookie:
            raise Exception("轻小说机翻站登录失败 cookie失效")
        # 数据库更新
        await update_cookie(cookie)

    async def get_book_list(self):
        start_page: int = 1 if read_config("start_page") < 1 else read_config("start_page")
        end_page: int = 1 if read_config("end_page") < 1 else read_config("end_page")
        if end_page < start_page:
            end_page = start_page
        for page in range(start_page, end_page + 1):
            log.info(f"轻小说机翻站开始爬取第{page}页...")
            url = f"{self.domain}/api/user/favored-web/default?page={page-1}&pageSize=30&query=&provider=kakuyomu%2Csyosetu%2Cnovelup%2Chameln%2Cpixiv%2Calphapolis&type=0&level=0&translate=0&sort=update"
            res = await request.get(url, self.header, self.session)
            if not res or not res.startswith("{"):
                return
            book_datas = json.loads(res)["items"]
            if not book_datas:
                log.info("轻小说机翻站列表解析失败")
                log.debug(res)
                return
            for book_data in book_datas:
                book = Book()
                book.source = "fish"
                # url作为id
                book.book_id = f"/novel/{book_data['providerId']}/{book_data['novelId']}"
                book.book_name = book_data["titleZh"]
                self.books.append(book)
                # 更新数据库
                await update_book(book)

    async def download(self, book: Book):
        log.info(f"{book.book_name} 开始下载epub...")
        url = f"{self.domain}/api{book.book_id}/file?mode=zh&translationsMode=priority&type=epub&filename={quote(book.book_name, safe='', encoding='utf-8')}.epub&translations=sakura"
        # windows 文件名限制
        char_map = {
            '/': ' ',
            '<': '《',
            '>': '》',
            ':': '：',
            '\\': ' ',
            '|': ' ',
            '?': '？',
            '*': ' '
        }
        # 替换不合法字符
        for char, replacement in char_map.items():
            book.book_name = book.book_name.replace(char, replacement)
        # linux 85 windows 127
        if len(book.book_name) > 85:
            book.book_name = book.book_name[:80] + "..."
        path = f"{read_config('epub_dir')}/{book.source}/{book.book_name}.epub"
        header = {
            "User-Agent": read_config("ua")
        }
        await request.download_file(url, header, path, self.session)
        log.info(f"{book.book_name} epub下载成功!")