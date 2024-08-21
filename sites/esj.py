import asyncio
import re
import uuid
from typing import Optional

from aiohttp import ClientSession
from lxml import html

from models.book import Book
from models.chapter import Chapter
from models.cookie import Cookie
from models.pic import Pic
from sites.abstract import Site

from sqlite.database import Database
from utils import config, request, log, common, image, epub


class Esj(Site):

    def __init__(self, session: ClientSession):
        self.session = session
        self.site = "esj"
        self.header = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        }
        thread = config.read("max_thread")
        if thread > 8:
            thread = 8
        self.thread = asyncio.Semaphore(thread)

    async def login(self):
        with Database() as db:
            self.cookie = db.cookie.get_one(self.site)
            if self.cookie:
                valid_bool = await self.valid_cookie()
                if valid_bool:
                    return
        cookie = Cookie()
        cookie.id = str(uuid.uuid4())
        cookie.source = self.site
        self.cookie = cookie
        await self.get_cookie()

    async def valid_cookie(self) -> bool:
        url = config.read("url_config")[self.site]["user"]
        self.header["Cookie"] = self.cookie.cookie
        res = await request.get(url=url, headers=self.header, session=self.session)
        if res and res.startswith("<!DOCTYPE html>"):
            log.info("%s校验缓存cookie成功，跳过登录" % self.site)
            return True
        return False

    async def get_cookie(self):
        log.info("%s开始登录..." % self.site)
        url = config.read("url_config")[self.site]["login"]
        login_data = {
            "email": config.read("login_info")[self.site]["username"],
            "pwd": config.read("login_info")[self.site]["password"],
            "remember_me": "on"
        }
        res = await request.post_data(url=url, headers=self.header, data=login_data, session=self.session)
        if res:
            self.cookie.cookie = "; ".join(res["headers"].getall("Set-Cookie"))
            self.header["Cookie"] = self.cookie.cookie
            with Database() as db:
                db.cookie.insert_or_update(self.cookie)
            log.info("%s登录成功" % self.site)
        else:
            raise Exception("登录失败！")

    async def get_books(self):
        # 白名单
        if config.read("white_list"):
            for book_url in config.read("white_list"):
                await self.build_book(book_url)
            return
        for page in range(config.read("start_page"), config.read("end_page") + 1):
            book_urls = await self.get_book_urls(page)
            if not book_urls:
                continue
            tasks = [asyncio.create_task(self.build_book(book_url)) for book_url in book_urls]
            if tasks:
                await asyncio.gather(*tasks)

    async def build_book(self, book_url: str):
        async with self.thread:
            res = await request.get(url=book_url, headers=self.header, session=self.session)
            book = self.build_book_from_text(res, book_url)
            if not book or not book.book_id:
                return
            with Database() as db:
                await db.book.insert_or_update(book, self.session)
            # 章节
            chapter_list = await self.build_chapters(book, res)
            # epub
            epub.build_epub(book, chapter_list)

    async def build_chapters(self, book: Book, text: str) -> list[Chapter]:
        chapter_xpaths = config.get_xpath(text, self.site, "chapter")
        with Database() as db:
            old_chapters = db.chapter.get_list(book.id)
        order = 1
        chapter_list = []
        for chapter_xpath in chapter_xpaths:
            chapter_body = html.fromstring(html.tostring(chapter_xpath))
            chapter_url = chapter_body.xpath("@href")[0]
            if not chapter_url:
                continue
            if "esjzone" not in chapter_url or ".html" not in chapter_url:
                # 外站用url做id
                chapter_id = chapter_url
            else:
                chapter_id = re.search(r"/(\d+)\.html", chapter_url).group(1)
            chapter = Chapter()
            chapter.id = str(uuid.uuid4())
            chapter.chapter_order = order
            chapter.book_table_id = book.id
            chapter.chapter_name = chapter_body.xpath("@data-title")[0]
            chapter.chapter_id = chapter_id
            order += 1
            if self.update_chapter(chapter, old_chapters):
                chapter_list.append(chapter)
                continue
            # 爬文本和插图
            await self.build_content(book, chapter, chapter_url)
            chapter_list.append(chapter)
        return chapter_list

    async def build_content(self, book: Book, chapter: Chapter, chapter_url: str):
        # 外站处理
        if chapter.chapter_id.startswith("http"):
            chapter.content = "<p>请至此链接下查看：" + chapter_url + "</p>"
            with Database() as db:
                db.chapter.insert_or_update(chapter)
            return
        text = await request.get(chapter_url, self.header, self.session)
        chapter.content = config.get_html(text, self.site, "content")
        if not chapter.content:
            return
        if "btn-send-pw" in chapter.content or "內文目前施工中" in chapter.content:
            # 密码章节跳过
            chapter.content = None
            with Database() as db:
                db.chapter.insert_or_update(chapter)
            return
        with Database() as db:
            db.chapter.insert_or_update(chapter)
        # 插图处理
        await self.build_images(book, chapter, text)
        log.info("%s 新获取章节内容" % chapter.chapter_name)

    async def build_images(self, book: Book, chapter: Chapter, text: str):
        with Database() as db:
            pics = db.pic.get_list(chapter.id)
        pic_urls = config.get_xpath(text, self.site, "pic")
        if not pic_urls:
            return
        for pic_url in pic_urls:
            # 排除非http链接
            if not pic_url.startswith("http"):
                return
            match_pic = common.find(pics, "pic_url", pic_url)
            if match_pic and match_pic.pic_path:
                continue
            pic = Pic()
            if match_pic:
                pic = match_pic
            else:
                pic.id = str(uuid.uuid4())
                pic.chapter_table_id = chapter.id
                pic.pic_url = pic_url
            # 下载图片
            await image.download(pic, self.site, book.book_id, chapter.chapter_id, self.session)
            with Database() as db:
                db.pic.insert_or_update(pic)

    def update_chapter(self, chapter: Chapter, old_chapters: Optional[Chapter]) -> bool:
        old_chapters = common.find_list(old_chapters, "chapter_id", chapter.chapter_id)
        if not old_chapters:
            return False
        old_chapter = old_chapters[0]
        if len(old_chapters) > 1:
            # 多匹配不做处理
            common.copy(old_chapter, chapter)
            return True
        if old_chapter.chapter_name != chapter.chapter_name \
                or old_chapter.chapter_order != chapter.chapter_order:
            old_chapter.chapter_name = chapter.chapter_name
            old_chapter.chapter_order = chapter.chapter_order
            with Database() as db:
                db.chapter.insert_or_update(old_chapter)
        common.copy(old_chapter, chapter)
        return True

    def build_book_from_text(self, text: str, book_url: str) -> Book:
        if not text:
            return None
        book = Book()
        book.id = str(uuid.uuid4())
        book.book_id = re.search(r"/(\d+)\.html$", book_url).group(1)
        book.source = self.site
        book.book_name = common.first(config.get_xpath(text, self.site, "title"))
        book.author = common.first(config.get_xpath(text, self.site, "author"))
        book.describe = common.join(config.get_xpath(text, self.site, "describe"), "\n")
        book.cover_url = common.first(config.get_xpath(text, self.site, "cover"))
        book.tags = common.join(config.get_xpath(text, self.site, "tags"))
        log.info("%s 书籍信息已获取" % book.book_name)
        return book

    async def get_book_urls(self, page: int) -> list:
        log.info("开始爬取%s第%d页" % (self.site, page))
        if config.read("get_collection"):
            page_url = config.read("url_config")[self.site]["collection"] % page
        else:
            page_url = config.read("url_config")[self.site]["page"] % page
        res = await request.get(url=page_url, headers=self.header, session=self.session)
        return self.get_book_urls_from_text(res)

    def get_book_urls_from_text(self, text: str) -> list:
        if not text:
            return None
        book_urls = []
        if config.read("get_collection"):
            book_xpaths = config.get_xpath(text, self.site, "collection")
        else:
            book_xpaths = config.get_xpath(text, self.site, "page")
        if not book_xpaths:
            return None
        for book_xpath in book_xpaths:
            book_url = config.read("url_config")[self.site]["book"] % book_xpath
            # 黑名单
            if config.read("black_list") and book_xpath in config.read("black_list"):
                continue
            book_urls.append(book_url)
        return book_urls
