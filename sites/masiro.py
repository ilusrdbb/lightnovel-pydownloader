import asyncio
import copy
import json
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
from utils import config, request, log, epub, common, image, push


class Masiro(Site):

    def __init__(self, session: ClientSession):
        self.session = session
        self.site = "masiro"
        self.header = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": config.read("url_config")["masiro"]["referer"] + "/admin",
            "Origin": config.read("url_config")["masiro"]["referer"]
        }
        thread = 1
        self.thread = asyncio.Semaphore(thread)
        self.token = ""

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
            # 推送calibre
            push.calibre(book)

    async def build_chapters(self, book: Book, text: str) -> list[Chapter]:
        parent_chapter_json = json.loads(config.get_xpath(text, self.site, "parent_chapter")[0])
        chapter_json = json.loads(config.get_xpath(text, self.site, "chapter")[0])
        if not chapter_json:
            return None
        with Database() as db:
            old_chapters = db.chapter.get_list(book.id)
        order = 1
        chapter_list = []
        for parent_chapter in parent_chapter_json:
            for chapter_data in chapter_json:
                if chapter_data["parent_id"] != parent_chapter["id"]:
                    continue
                chapter_id = str(chapter_data["id"])
                chapter_url = config.read("url_config")[self.site]["chapter"] % chapter_data["id"]
                chapter = Chapter()
                chapter.id = str(uuid.uuid4())
                chapter.chapter_order = order
                chapter.book_table_id = book.id
                chapter.chapter_name = chapter_data["title"]
                chapter.chapter_id = chapter_id
                chapter.last_update_time = common.time(chapter_data["episode_update_time"])
                order += 1
                if self.update_chapter(chapter, old_chapters):
                    chapter_list.append(chapter)
                    continue
                # 爬文本和插图
                await self.build_content(book, chapter, chapter_url, chapter_data["cost"])
                chapter_list.append(chapter)
        return chapter_list

    async def build_content(self, book: Book, chapter: Chapter, chapter_url: str, cost: int):
        text = await request.get(chapter_url, self.header, self.session)
        if cost > 0 and "立即打钱" in text:
            # 打钱处理
            chapter.purchase_fail_flag = 1
            if config.read("is_purchase") and cost <= config.read("max_purchase"):
                text = await self.pay(book, chapter, chapter_url, cost)
        else:
            chapter.content = config.get_html(text, self.site, "content")
        with Database() as db:
            db.chapter.insert_or_update(chapter)
        # 插图处理
        await self.build_images(book, chapter, text)
        log.info("%s 新获取章节内容" % chapter.chapter_name)

    async def pay(self, book: Book, chapter: Chapter, chapter_url: str, cost: int) -> str:
        log.info("%s 开始打钱..花费: %s金币" % (book.book_name, str(cost)))
        cost_url = config.read("url_config")[self.site]["cost"]
        cost_param = {
            "type": 2,
            "object_id": chapter.chapter_id,
            "cost": cost
        }
        cost_header = copy.deepcopy(self.header)
        cost_header['x-csrf-token'] = self.token
        cost_res = await request.post_json(url=cost_url, headers=cost_header, json=cost_param, session=self.session)
        if cost_res and json.loads(cost_res)['code'] == 1:
            # 打钱成功 刷新文本
            log.info("%s 打钱成功！" % book.book_name)
            text = await request.get(chapter_url, self.header, self.session)
            chapter.content = config.get_html(text, self.site, "content")
            chapter.purchase_fail_flag = 0
            return text
        return None

    async def build_images(self, book: Book, chapter: Chapter, text: str):
        if not text:
            return
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
            # 下载图片
            await image.download(pic, self.site, book.book_id, chapter.chapter_id, self.session)
            with Database() as db:
                db.pic.insert_or_update(pic)

    def update_chapter(self, chapter: Chapter, old_chapters: Optional[Chapter]) -> bool:
        old_chapter = common.find(old_chapters, "chapter_id", chapter.chapter_id)
        if not old_chapter:
            return False
        if old_chapter.purchase_fail_flag and old_chapter.purchase_fail_flag == 1:
            # 打钱失败的
            common.copy(old_chapter, chapter)
            return False
        if old_chapter.chapter_name != chapter.chapter_name \
                or old_chapter.chapter_order != chapter.chapter_order:
            old_chapter.chapter_name = chapter.chapter_name
            old_chapter.chapter_order = chapter.chapter_order
            with Database() as db:
                db.chapter.insert_or_update(old_chapter)
        if old_chapter.last_update_time < chapter.last_update_time:
            old_chapter.last_update_time = chapter.last_update_time
            with Database() as db:
                db.chapter.insert_or_update(old_chapter)
            # 后续需要更新文本
            common.copy(old_chapter, chapter)
            return False
        common.copy(old_chapter, chapter)
        return True

    def build_book_from_text(self, text: str, book_url: str) -> Book:
        if not text:
            return None
        book = Book()
        book.id = str(uuid.uuid4())
        book.book_id = book_url.split('?novel_id=')[-1]
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
        book_datas = json.loads(text)
        if book_datas["novels"]:
            for book_data in book_datas["novels"]:
                book_url = config.read("url_config")[self.site]["book"] % book_data["id"]
                # 黑名单
                if config.read("black_list") and book_url in config.read("black_list"):
                    continue
                book_urls.append(book_url)
        return book_urls

    async def login(self):
        with Database() as db:
            self.cookie = db.cookie.get_one(self.site)
            if self.cookie:
                valid_bool = await self.valid_cookie()
                if valid_bool:
                    return
        if not config.read("flaresolverr_url"):
            log.info("真白萌需要在配置中填写flaresolverr_url")
            return
        cookie = Cookie()
        cookie.id = str(uuid.uuid4())
        cookie.source = self.site
        self.cookie = cookie
        await self.get_cookie()

    async def valid_cookie(self) -> bool:
        url = config.read("url_config")[self.site]["user"]
        self.header["Cookie"] = self.cookie.cookie
        self.header["User-Agent"] = self.cookie.uid
        self.token = self.cookie.token
        res = await request.get(url=url, headers=self.header, session=self.session)
        if res and "csrf-token" in res:
            return True
        return False

    async def get_cookie(self):
        url = config.read("url_config")[self.site]["login"]
        cf_bool = await self.fuck_cf()
        if not cf_bool:
            raise Exception("真白萌破cf盾失败，停止爬取")
        await self.get_token()
        login_data = {
            "username": config.read("login_info")[self.site]["username"],
            "password": config.read("login_info")[self.site]["password"],
            "remember": "1",
            "_token": self.token
        }
        res = await request.post_data(url=url, headers=self.header, data=login_data, session=self.session)
        if res:
            self.cookie.cookie = self.header["Cookie"] + "; ".join(res["headers"].getall("Set-Cookie"))
            self.cookie.uid = self.header["User-Agent"]
            self.cookie.token = self.token
            self.header["Cookie"] = self.cookie.cookie
            with Database() as db:
                db.cookie.insert_or_update(self.cookie)
            log.info("%s 登录成功" % self.site)
        else:
            raise Exception("登录失败！")

    async def get_token(self):
        url = config.read("url_config")[self.site]["login"]
        res = await request.get(url=url, headers=self.header, session=self.session)
        if res:
            self.token = config.get_xpath(res, self.site, "token")[0]

    async def fuck_cf(self) -> bool:
        log.info("真白萌开始破cf盾...")
        url = config.read("flaresolverr_url")
        headers = {
            'content-type': 'application/json'
        }
        data = {
            "cmd": "request.get",
            "url": config.read("url_config")[self.site]["login"],
            "maxTimeout": 60000
        }
        res = await request.post_json(url=url, headers=headers, json=data, session=self.session)
        if res:
            res_json = json.loads(res)
            self.header["User-Agent"] = res_json["solution"]["userAgent"]
            for cf_cookie in res_json["solution"]["cookies"]:
                if cf_cookie["name"] == "cf_clearance":
                    self.header["Cookie"] = "cf_clearance=" + cf_cookie["value"] + ";"
                    log.info("真白萌破盾成功！")
                    return True
        return False
