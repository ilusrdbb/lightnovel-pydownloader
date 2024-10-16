import asyncio
import re
import uuid
from typing import Optional

from aiohttp import ClientSession
from lxml import html

from js import runjs
from models.book import Book
from models.chapter import Chapter
from models.pic import Pic
from sites.abstract import Site
from sqlite.database import Database
from utils import config, request, log, common, image, epub


class Yuri(Site):

    def __init__(self, session: ClientSession):
        self.session = session
        self.site = "yuri"
        self.header = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        }
        thread = config.read("max_thread")
        if thread > 4:
            thread = 4
        if config.read("push_calibre")["enabled"]:
            thread = 1
        self.thread = asyncio.Semaphore(thread)

    async def login(self):
        if not config.read("login_info")[self.site]["cookie"]:
            log.info("%s cookie未配置，跳过" % self.site)
            raise Exception()
        self.header["Cookie"] = config.read("login_info")[self.site]["cookie"]
        await self.valid_cookie()

    async def valid_cookie(self) -> bool:
        log.info("%s开始校验cookie..." % self.site)
        url = config.read("url_config")[self.site]["user"]
        res = await request.get(url=url, headers=self.header, session=self.session)
        if res and "<title>用户组" in res:
            log.info("%s cookie校验通过" % self.site)
            # await self.get_cookie()
        else:
            log.info("cookie校验失败！")
            raise Exception()

    async def get_cookie(self):
        # egg
        url = "https://bbs.yamibo.com/plugin.php?id=zqlj_sign"
        res = await request.get(url=url, headers=self.header, session=self.session)
        page_body = html.fromstring(res)
        form_hash = page_body.xpath("//input[@name='formhash']/@value")[0]
        sign_url = "https://bbs.yamibo.com/plugin.php?id=zqlj_sign&sign=" + form_hash
        await request.get(url=sign_url, headers=self.header, session=self.session)
        log.info("%s 签到成功！" % self.site)

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
            res_turple = await self.handle_dsign(book_url)
            _book_url = res_turple[0]
            res = res_turple[1]
            book = self.build_book_from_text(res, _book_url)
            if not book or not book.book_id:
                return
            with Database() as db:
                await db.book.insert_or_update(book, self.session)
            author_id = common.first(config.get_xpath(res, self.site, "author"))
            # 只看作者 全部页数的全部数据
            text_list = await self.get_content_page(book, author_id)
            if not text_list:
                return
            # 章节
            all_chapter_list = []
            order_dict = {"order": 1}
            for text in text_list:
                chapter_list = await self.build_chapters(book, text, order_dict)
                if chapter_list:
                    all_chapter_list += chapter_list
            # epub
            epub.build_epub(book, all_chapter_list)

    async def get_content_page(self, book: Book, author_id: str) -> list:
        # 只看作者
        author_url = config.read('url_config')[self.site]["chapter"] % (book.book_id, "1", author_id)
        author_res_turple = await self.handle_dsign(author_url)
        first_res = author_res_turple[1]
        if not first_res:
            return None
        result_list = [first_res]
        # 获取页数
        page_size_xpath = common.first(config.get_xpath(first_res, self.site, "size"))
        if not page_size_xpath:
            page_size = 1
        else:
            page_size = int(re.findall("\d+", page_size_xpath)[0])
        if page_size == 1:
            return result_list
        for page in range(2, page_size + 1):
            url = config.read('url_config')[self.site]["chapter"] % (book.book_id, str(page), author_id)
            res_turple = await self.handle_dsign(url)
            result_list.append(res_turple[1])
        return result_list

    async def handle_dsign(self, url: str):
        _url = url
        res = await request.get(url=url, headers=self.header, session=self.session)
        if res.startswith("<script"):
            # 反爬处理
            _url = config.read("url_config")[self.site]["dsign"] % runjs.get_dsign(res)
            res = await request.get(url=_url, headers=self.header, session=self.session)
        return _url, res

    async def build_chapters(self, book: Book, text: str, order_dict: dict) -> list[Chapter]:
        chapter_xpaths = config.get_xpath(text, self.site, "chapter")
        if not chapter_xpaths:
            return None
        order = order_dict["order"]
        chapter_list = []
        for xpath in chapter_xpaths:
            chapter_html = html.tostring(xpath, pretty_print=True, encoding="unicode")
            if not chapter_html:
                continue
            chapter = Chapter()
            chapter.id = str(uuid.uuid4())
            chapter.chapter_order = order
            chapter.book_table_id = book.id
            chapter.chapter_name = str(order)
            chapter.chapter_id = str(order)
            order += 1
            order_dict["order"] = order
            # 爬文本和插图
            await self.build_content(book, chapter, chapter_html)
            chapter_list.append(chapter)
        return chapter_list

    async def build_content(self, book: Book, chapter: Chapter, text: str):
        chapter.content = text
        # img标签特殊处理
        chapter.content = chapter.content.replace("src=\"static/image/common/none.gif\"", "")
        chapter.content = chapter.content.replace("file=\"", "src=\"")
        with Database() as db:
            db.chapter.insert_or_update(chapter)
        # 插图处理
        await self.build_images(book, chapter, text)
        log.info("%s楼 获取内容" % chapter.chapter_name)

    async def build_images(self, book: Book, chapter: Chapter, text: str):
        with Database() as db:
            pics = db.pic.get_list(chapter.id)
        pic_urls = config.get_xpath(text, self.site, "pic")
        if not pic_urls:
            return
        for pic_url in pic_urls:
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
            # 论坛自己的图床
            if not pic_url.startswith("http"):
                pic_full_url = config.read("url_config")[self.site]["book"] % pic_url
                pic.pic_url = pic_full_url
            # 下载图片
            await image.download(pic, self.site, book.book_id, chapter.chapter_id, self.session)
            pic.pic_url = pic_url
            with Database() as db:
                db.pic.insert_or_update(pic)

    def build_book_from_text(self, text: str, book_url: str) -> Book:
        if not text:
            return None
        book = Book()
        book.id = str(uuid.uuid4())
        book.book_id = book_url.split('-')[1]
        book.source = self.site
        book.book_name = common.first(config.get_xpath(text, self.site, "title"))
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
            if "javascript" in book_xpath:
                continue
            if "thread-535989-" in book_xpath:
                # 排除置顶专楼
                continue
            book_url = config.read("url_config")[self.site]["book"] % book_xpath
            # 黑名单
            if config.read("black_list") and book_xpath in config.read("black_list"):
                continue
            book_urls.append(book_url)
        return book_urls
