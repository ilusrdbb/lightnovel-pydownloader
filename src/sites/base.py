import asyncio
import traceback
from abc import ABC, abstractmethod
from asyncio import Semaphore
from typing import List, Dict

from aiohttp import ClientSession

from src.db import cookie
from src.epub.epub import build_epub
from src.epub.txt import build_txt
from src.models.book import Book
from src.models.chapter import Chapter
from src.models.cookie import Cookie
from src.utils.config import read_config
from src.utils.log import log


class BaseSite(ABC):

    def __init__(self, session: ClientSession):
        self.site: str = None
        self.session: ClientSession = session
        self.cookie: Cookie = None
        self.books: List[Book] = []
        # 默认线程 最大写死8线程别把网站玩崩了
        thread_counts = 8 if read_config("max_thread") > 8 else read_config("max_thread")
        if read_config("push_calibre")["enabled"] or read_config("max_thread") < 1:
            thread_counts = 1
        self.threads: Semaphore = asyncio.Semaphore(thread_counts)
        # 白名单
        self.white_list: List[str] = [] if len(read_config("sites")) > 1 else read_config("white_list")
        # 默认请求头
        self.header: Dict[str, str] = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "User-Agent": read_config("ua")
        }
        # 图片下载请求头
        self.pic_header: Dict[str, str] = {
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, zstd",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "User-Agent": read_config("ua")
        }
        # 爬取范围
        self.start_page: int = 1 if read_config("start_page") < 1 else read_config("start_page")
        self.end_page: int = 1 if read_config("end_page") < 1 else read_config("end_page")
        if self.end_page < self.start_page:
            self.end_page = self.start_page

    async def run(self):
        try:
            # 校验cookie
            self.cookie = await cookie.get_cookie(self.site)
            if self.cookie and self.cookie.cookie:
                self.header["Cookie"] = self.cookie.cookie
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
            # 多线程开启爬虫
            tasks = [asyncio.create_task(self.start_task(book)) for book in self.books]
            await asyncio.gather(*tasks)
            # 签到
            if read_config("sign"):
                await self.sign()
        except Exception as e:
            log.info(str(e))
            log.debug(traceback.print_exc())

    async def start_task(self, book: Book):
        try:
            loop = asyncio.get_running_loop()
            async with self.threads:
                # 构造完整书籍信息
                await self.build_book_info(book)
                log.info(f"{book.book_name} {self.site}书籍信息已获取")
                # 构造章节列表
                log.info(f"{self.site}开始获取章节列表...")
                await self.build_chapter_list(book)
                if not book.chapters:
                    log.info(f"{self.site}未获取到章节")
                    return
                log.info(f"{book.book_name} {self.site}章节信息已全部获取")
                # 构造图片
                for chapter in book.chapters:
                    if chapter.content:
                        await self.build_pic_list(chapter)
                # epub
                await loop.run_in_executor(None, build_epub, book)
                # txt
                if read_config("convert_txt"):
                    await loop.run_in_executor(None, build_txt, book)
        except Exception as e:
            log.info(str(e))
            log.debug(traceback.print_exc())

    @abstractmethod
    async def valid_cookie(self) -> bool:
        pass

    @abstractmethod
    async def login(self):
        pass

    @abstractmethod
    async def get_book_list(self):
        pass

    @abstractmethod
    async def build_book_info(self, book: Book):
        pass

    @abstractmethod
    async def build_chapter_list(self, book: Book):
        pass

    @abstractmethod
    async def build_pic_list(self, chapter: Chapter):
        pass

    @abstractmethod
    async def build_content(self, chapter: Chapter):
        pass

    @abstractmethod
    async def sign(self):
        pass