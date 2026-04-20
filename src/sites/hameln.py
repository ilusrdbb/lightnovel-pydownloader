import asyncio
import re
from typing import List

from aiohttp import ClientSession
from lxml import html

from src.db.book import update_book
from src.db.chapter import get_chapter_list, update_chapter
from src.db.cookie import update_cookie
from src.db.pic import get_pic_list, update_pic, insert_pic
from src.models.book import Book
from src.models.chapter import Chapter
from src.models.cookie import Cookie
from src.models.pic import Pic
from src.sites.base import BaseSite
from src.utils import request, common
from src.utils.config import read_config
from src.utils.dsign import get_dsign
from src.utils.log import log


class Hameln(BaseSite):

    def __init__(self, session: ClientSession):
        super().__init__(session)
        self.site: str = "hameln"
        self.domain: str = read_config("domain")["hameln"]
        # 容易触发反爬强制单线程
        self.threads = asyncio.Semaphore(1)

    async def valid_cookie(self) -> bool:
        url = f"{self.domain}/?mode=favo"
        res = await request.get(url, self.header, self.session)
        if res:
            log.info("hameln校验cookie成功")
            return True
        log.info("hameln cookie失效")
        return False

    async def login(self):
        cookie = Cookie()
        cookie.source = "hameln"
        if not read_config("login_info")["hameln"]["cookie"]:
            raise Exception("hameln未配置登录信息")
        cookie.cookie = read_config("login_info")["hameln"]["cookie"]
        # 再校验一次cookie
        self.cookie = cookie
        self.header["Cookie"] = cookie.cookie
        is_effective_cookie = await self.valid_cookie()
        if not is_effective_cookie:
            raise Exception("hameln登录失败 cookie失效")
        # 数据库更新
        await update_cookie(cookie)

    async def get_book_list(self):
        # 白名单
        if read_config("white_list"):
            for white_book_id in common.handle_url_list(read_config("white_list"), "hameln"):
                book = Book()
                book.source = "hameln"
                book.book_id = white_book_id
                self.books.append(book)
            return
        # 正常爬取
        for page in range(self.start_page, self.end_page + 1):
            log.info(f"hameln开始爬取第{page}页...")
            url = f"{self.domain}/?mode=favo"
            res = await request.get(url, self.header, self.session)
            if not res:
                return
            book_urls = common.get_xpath(res, "hameln", "collection")
            if not book_urls:
                log.info("hameln列表解析失败")
                log.debug(res)
                return
            for book_url in book_urls:
                book = Book()
                book.source = "hameln"
                book.book_id = common.get_book_id(book_url, "hameln")
                # 黑名单跳过
                if book.book_id in common.handle_url_list(read_config("black_list"), "hameln"):
                    continue
                self.books.append(book)

    async def build_book_info(self, book: Book):
        url = f"{self.domain}/novel/{book.book_id}/"
        res = await request.get(url, self.header, self.session)
        if not res:
            log.info(f"{url} hameln获取书籍信息失败")
            return
        book.book_name = common.first(common.get_xpath(res, "hameln", "title"))
        book.author = common.first(common.get_xpath(res, "hameln", "author"))
        book.describe = common.first(common.get_xpath(res, "hameln", "describe"))
        book.chapter_xpaths = common.get_xpath(res, "hameln", "chapter")
        # 更新数据库
        await update_book(book)

    async def build_chapter_list(self, book: Book):
        if not book.chapter_xpaths:
            return
        # 数据库已存章节
        old_chapters = await get_chapter_list(book.id)
        chapters = []
        order = 1
        for chapter_xpath in book.chapter_xpaths:
            chapter_body = html.fromstring(html.tostring(chapter_xpath))
            chapter_url = common.first(chapter_body.xpath("@href"))
            log.debug(chapter_url)
            chapter_id = chapter_url.split('/')[-1].split('.')[0]
            if not chapter_id:
                log.info(f"hameln章节地址配置错误，跳过本章 {chapter_url}")
                continue
            chapter_name = common.first(chapter_body.xpath("text()"))
            # 匹配数据库已存章节
            chapter = common.find(old_chapters, "chapter_id", chapter_id)
            if chapter:
                chapter.book_id = book.book_id
                chapter.pics = []
                if chapter.chapter_order != order or chapter.chapter_name != chapter_name:
                    # 标题或顺序改变 需要更新
                    chapter.chapter_order = order
                    chapter.chapter_name = chapter_name
                    await update_chapter(chapter)
            else:
                # 新章节
                chapter = Chapter()
                chapter.chapter_order = order
                chapter.book_table_id = book.id
                chapter.chapter_id = chapter_id
                chapter.chapter_name = chapter_name
                chapter.book_id = book.book_id
                # 获取内容
                await self.build_content(chapter)
                # 更新数据库
                await update_chapter(chapter)
            order += 1
            chapters.append(chapter)
        book.chapters = chapters

    async def build_content(self, chapter: Chapter):
        log.info(f"{chapter.chapter_name} hameln开始获取章节内容...")
        url = f"{self.domain}/novel/{chapter.book_id}/{chapter.chapter_id}.html"
        text = await request.get(url, self.header, self.session)
        if not text:
            log.debug(url)
            return
        chapter.content = common.get_html(text, "hameln", "content")
        if not chapter.content:
            log.info(f"hameln章节无内容 {chapter.chapter_name}")
            return
        log.info(f"{chapter.chapter_name} hameln新获取章节内容")

    async def build_pic_list(self, chapter: Chapter):
        pass

    async def sign(self):
        pass

