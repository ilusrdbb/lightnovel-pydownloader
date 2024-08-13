import asyncio
import copy
import uuid
from typing import Optional

from aiohttp import ClientSession

from models.book import Book
from models.chapter import Chapter
from models.cookie import Cookie
from models.pic import Pic
from sites.abstract import Site
from sqlite.database import Database
from utils import config, request, common, log, epub, image, push


class Lk(Site):

    def __init__(self, session: ClientSession):
        self.session = session
        self.site = "lk"
        self.header = {
            "content-type": "application/json; charset=UTF-8",
            "accept-encoding": "gzip",
            "host": "api.lightnovel.us",
            "user-agent": "Dart/2.10 (dart:io)"
        }
        thread = config.read("max_thread")
        if thread > 4:
            thread = 4
        self.thread = asyncio.Semaphore(thread)
        self.param = {
            "platform": "android",
            "client": "app",
            "sign": "",
            "ver_name": "0.11.52",
            "ver_code": "192",
            "d": {
                "uid": "",
                "security_key": ""
            },
            "gz": 1
        }

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
        self.param["d"]["uid"] = self.cookie.uid
        self.param["d"]["security_key"] = self.cookie.token
        res = await request.post_json(url=url, headers=self.header, json=self.param, session=self.session)
        if res and common.unzip(res).get("code") == 0:
            return True
        return False

    async def get_cookie(self):
        url = config.read("url_config")[self.site]["login"]
        param = self.param
        param["is_encrypted"] = 0
        param["d"] = {
            "username": config.read("login_info")[self.site]["username"],
            "password": config.read("login_info")[self.site]["password"]
        }
        res = await request.post_json(url=url, headers=self.header, json=param, session=self.session)
        if res and common.unzip(res)["code"] == 0:
            self.cookie.uid = common.unzip(res)["data"]["uid"]
            self.cookie.token = common.unzip(res)["data"]["security_key"]
            self.param["d"]["uid"] = self.cookie.uid
            self.param["d"]["security_key"] = self.cookie.token
            with Database() as db:
                db.cookie.insert_or_update(self.cookie)
            log.info("%s 登录成功" % self.site)
        else:
            raise Exception("登录失败！")

    async def get_books(self):
        # 白名单 sid
        if config.read("white_list"):
            for sid in config.read("white_list"):
                if sid == 0:
                    continue
                await self.build_book({"sid": sid, "aid": 0})
            return
        for page in range(config.read("start_page"), config.read("end_page") + 1):
            page_books = await self.get_page_list(page)
            if not page_books:
                continue
            tasks = [asyncio.create_task(self.build_book(page_book)) for page_book in page_books]
            if tasks:
                await asyncio.gather(*tasks)

    async def build_book(self, page_book: dict):
        async with self.thread:
            # 屏蔽公告等
            black_aid = [969547, 1113228, 1099310, 1048596]
            if page_book["aid"] in black_aid:
                return
            sid = page_book["sid"]
            if sid == 0:
                book = self.build_book_from_page(page_book)
            else:
                # 黑名单
                if config.read("black_list") and sid in config.read("black_list"):
                    return
                book_url = config.read("url_config")[self.site]["book"]
                param = copy.deepcopy(self.param)
                param["d"]["sid"] = sid
                res = await request.post_json(url=book_url, headers=self.header, json=param, session=self.session)
                book = self.build_book_from_res(res)
            if not book or not book.book_id:
                return
            with Database() as db:
                await db.book.insert_or_update(book, self.session)
            # 章节
            if sid == 0:
                chapter_list = [await self.build_chapter(book, page_book)]
            else:
                chapter_list = await self.build_chapters(book, res)
            # epub
            epub.build_epub(book, chapter_list)

    async def build_chapter(self, book: Book, page_book: dict) -> Chapter:
        with Database() as db:
            old_chapter = common.first(db.chapter.get_list(book.book_id))
        chapter = Chapter()
        chapter.id = str(uuid.uuid4())
        chapter.chapter_order = 1
        chapter.book_table_id = book.id
        chapter.chapter_name = book.book_name
        chapter.chapter_id = book.book_id
        chapter.last_update_time = common.time(page_book["last_time"])
        if self.update_chapter(chapter, [old_chapter]):
            return chapter
        await self.build_content(book, chapter)
        return chapter

    async def build_chapters(self, book: Book, res: str) -> list[Chapter]:
        if res and common.unzip(res)["code"] == 0:
            chapter_datas = common.unzip(res)["data"]["articles"]
            with Database() as db:
                old_chapters = db.chapter.get_list(book.id)
            order = 1
            chapter_list = []
            for chapter_data in chapter_datas:
                chapter = Chapter()
                chapter.id = str(uuid.uuid4())
                chapter.chapter_order = order
                chapter.book_table_id = book.id
                chapter.chapter_name = chapter_data["title"]
                chapter.chapter_id = str(chapter_data["aid"])
                chapter.last_update_time = common.time(chapter_data["last_time"])
                order += 1
                if self.update_chapter(chapter, old_chapters):
                    chapter_list.append(chapter)
                    continue
                await self.build_content(book, chapter)
                chapter_list.append(chapter)
            return chapter_list
        return None

    async def build_content(self, book: Book, chapter: Chapter):
        pic_urls = []
        chapter_url = config.read("url_config")[self.site]["chapter"]
        param = copy.deepcopy(self.param)
        param["d"]["aid"] = chapter.chapter_id
        param["d"]["simple"] = 0
        res = await request.post_json(url=chapter_url, headers=self.header, json=param, session=self.session)
        if res and common.unzip(res)["code"] == 0:
            chapter_data = common.unzip(res)["data"]
            if chapter_data.get("pay_info"):
                # 打钱处理
                if chapter_data.get("pay_info")["is_paid"] == 0 and config.read("is_purchase"):
                    chapter.purchase_fail_flag = 1
                    cost = chapter_data.get("pay_info")["price"]
                    if cost <= config.read("max_purchase"):
                        await self.pay(book, chapter, cost, pic_urls)
                elif chapter_data.get("pay_info")["is_paid"] == 1:
                    chapter.purchase_fail_flag = 0
                    chapter.content = common.bbcode_to_html(chapter_data["content"], chapter_data, pic_urls)
                else:
                    chapter.purchase_fail_flag = 1
            else:
                chapter.content = common.bbcode_to_html(chapter_data["content"], chapter_data, pic_urls)
        with Database() as db:
            db.chapter.insert_or_update(chapter)
        # 插图处理
        await self.build_images(book, chapter, pic_urls)
        log.info("%s 新获取章节内容" % chapter.chapter_name)

    async def pay(self, book: Book, chapter: Chapter, cost: int, pic_urls: list):
        log.info("%s 开始打钱..花费: %s轻币" % (book.book_name, str(cost)))
        cost_url = config.read("url_config")[self.site]["cost"]
        cost_param = copy.deepcopy(self.param)
        cost_param["d"]["goods_id"] = 1
        cost_param["d"]["params"] = int(chapter.chapter_id)
        cost_param["d"]["price"] = cost
        cost_param["d"]["number"] = 1
        cost_param["d"]["total_price"] = cost
        cost_res = await request.post_json(url=cost_url, headers=self.header, json=cost_param, session=self.session)
        if cost_res and common.unzip(cost_res)["code"] == 0:
            # 打钱成功 刷新文本
            log.info("%s 打钱成功！" % book.book_name)
            chapter_url = config.read("url_config")[self.site]["chapter"]
            param = copy.deepcopy(self.param)
            param["d"]["aid"] = chapter.chapter_id
            param["d"]["simple"] = 0
            res = await request.post_json(url=chapter_url, headers=self.header, json=param, session=self.session)
            if res and common.unzip(res)["code"] == 0:
                chapter_data = common.unzip(res)["data"]
                chapter.content = common.bbcode_to_html(chapter_data["content"], chapter_data, pic_urls)
                if chapter.content:
                    chapter.purchase_fail_flag = 0

    async def build_images(self, book: Book, chapter: Chapter, pic_urls: list):
        if not chapter.content:
            return
        with Database() as db:
            pics = db.pic.get_list(chapter.id)
        if not pic_urls:
            return
        for pic_url in pic_urls:
            match_pic = common.find(pics, "pic_url", pic_url["url"])
            if not match_pic and pic_url["id"]:
                match_pic = common.find(pics, "pic_id", pic_url["id"])
            if match_pic and match_pic.pic_path:
                continue
            pic = Pic()
            if match_pic:
                pic = match_pic
            else:
                pic.id = str(uuid.uuid4())
                pic.chapter_table_id = chapter.id
                pic.pic_url = pic_url["url"]
                pic.pic_id = pic_url["id"]
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

    def build_book_from_res(self, res: str) -> Book:
        if res and common.unzip(res)["code"] == 0:
            book_dict = common.unzip(res)
            if not book_dict["data"]:
                return None
            book = Book()
            book.id = str(uuid.uuid4())
            book.book_id = str(book_dict["data"]["sid"])
            book.source = self.site
            book.book_name = book_dict["data"]["name"]
            book.author = book_dict["data"]["author"]
            book.cover_url = book_dict["data"]["cover"]
            book.describe = book_dict["data"]["intro"]
            log.info("%s 书籍信息已获取" % book.book_name)
            return book
        return None

    def build_book_from_page(self, page_book: dict) -> Book:
        book = Book()
        book.id = str(uuid.uuid4())
        book.book_id = str(page_book["aid"])
        book.source = self.site
        book.book_name = page_book["title"]
        book.cover_url = page_book["cover"]
        log.info("%s 书籍信息已获取" % book.book_name)
        return book

    async def get_page_list(self, page: int) -> list:
        log.info("开始爬取%s第%d页" % (self.site, page))
        param = self.param
        param["d"]["page"] = page
        param["d"]["pageSize"] = 20
        if config.read('get_collection'):
            page_url = config.read("url_config")[self.site]["collection"]
            param["d"]["type"] = 1
            # class 1 单本
            param["d"]["class"] = 1
        else:
            page_url = config.read("url_config")[self.site]["page"]
            param["d"]["parent_gid"] = 3
            # gid 106 最新 gid 107 整卷
            param["d"]["gid"] = 106
        res = await request.post_json(url=page_url, headers=self.header, json=param, session=self.session)
        if res and common.unzip(res)["code"] == 0:
            if config.read('get_collection'):
                # class 2 合集
                param["d"]["class"] = 2
                res2 = await request.post_json(url=page_url, headers=self.header, json=param, session=self.session)
                return common.unzip(res)["data"]["list"] + common.unzip(res2)["data"]["list"]
            else:
                return common.unzip(res)["data"]["list"]
        return None