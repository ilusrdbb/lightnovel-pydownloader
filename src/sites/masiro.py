import copy
import json
import os

from aiohttp import ClientSession

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
from src.utils.log import log


class Mairo(BaseSite):

    def __init__(self, session: ClientSession):
        super().__init__(session)
        self.site: str = "masiro"
        self.domain: str = read_config("domain")["masiro"]
        self.token:str = None
        self.header["Referer"] = f"{self.domain}/admin"
        self.header["Origin"] = self.domain

    async def valid_cookie(self) -> bool:
        url = f"{self.domain}/admin/userCenterShow"
        self.header["User-Agent"] = self.cookie.uid
        res = await request.get(url, self.header, self.session)
        if res and "csrf-token" in res:
            log.info("真白萌校验cookie成功")
            return True
        log.info("真白萌cookie失效")
        log.debug(res)
        return False

    async def login(self):
        cookie = Cookie()
        cookie.source = "masiro"
        if (not read_config("login_info")["masiro"]["username"]
                or not read_config("login_info")["masiro"]["password"]
                or not read_config("login_info")["masiro"]["flaresolverr_url"]):
            if read_config("login_info")["masiro"]["cookie"] and read_config("login_info")["masiro"]["useragent"]:
                self.header["Cookie"] = read_config("login_info")["masiro"]["cookie"]
                self.header["User-Agent"] = read_config("login_info")["masiro"]["useragent"]
                # 拿token
                await self.get_token(f"{self.domain}/admin/userCenterShow")
            else:
                raise Exception("真白萌未配置登录信息")
        else:
            # 破cf盾
            cf_bool = await self.fuck_cf()
            if not cf_bool:
                log.info("真白萌破cf盾失败，停止爬取")
                raise Exception("真白萌破cf盾失败")
            # 拿token
            url = f"{self.domain}/admin/auth/login"
            await self.get_token(url)
            # 登录
            login_data = {
                "username": read_config("login_info")["masiro"]["username"],
                "password": read_config("login_info")["masiro"]["password"],
                "remember": "1",
                "_token": self.token
            }
            res = await request.post_data(url=url, headers=self.header, data=login_data, session=self.session)
            if res:
                self.header["Cookie"] = self.header["Cookie"] + "; ".join(res["headers"].getall("Set-Cookie"))
                log.debug(res)
            else:
                raise Exception("真白萌登录失败")
        # 再校验一次cookie
        self.cookie = cookie
        cookie.cookie = self.header["Cookie"]
        cookie.uid = self.header["User-Agent"]
        cookie.token = self.token
        is_effective_cookie = await self.valid_cookie()
        if not is_effective_cookie:
            raise Exception("真白萌登录失败 cookie失效")
        # 数据库更新
        await update_cookie(cookie)

    async def get_book_list(self):
        # 白名单
        if read_config("white_list"):
            for white_book_id in common.handle_url_list(read_config("white_list"), "masiro"):
                book = Book()
                book.source = "masiro"
                book.book_id = white_book_id
                self.books.append(book)
            return
        # 正常爬取
        for page in range(self.start_page, self.end_page + 1):
            log.info(f"真白萌开始爬取第{page}页...")
            if read_config("get_collection"):
                url = f"{self.domain}/admin/loadMoreNovels?page={page}&collection=1"
            else:
                url = f"{self.domain}/admin/loadMoreNovels?ori=0&page={page}"
            res = await request.get(url, self.header, self.session)
            if not res:
                return
            book_json = json.loads(res)
            if not book_json["novels"]:
                log.debug(res)
                return
            for book_data in book_json["novels"]:
                book = Book()
                book.source = "masiro"
                book.book_id = book_data["id"]
                # 黑名单跳过
                if book.book_id in common.handle_url_list(read_config("black_list"), "masiro"):
                    continue
                self.books.append(book)

    async def build_book_info(self, book: Book):
        url = f"{self.domain}/admin/novelView?novel_id={book.book_id}"
        res = await request.get(url, self.header, self.session)
        if not res:
            log.info(f"{url} 真白萌获取书籍信息失败")
            return
        book.book_name = common.first(common.get_xpath(res, "masiro", "title"))
        book.author = common.first(common.get_xpath(res, "masiro", "author"))
        book.describe = common.join(common.get_xpath(res, "masiro", "describe"), "\n")
        book.cover_url = common.first(common.get_xpath(res, "masiro", "cover"))
        book.tags = common.join(common.get_xpath(res, "masiro", "tags"))
        book.page_text = res
        # 更新数据库
        download_cover = await update_book(book)
        if download_cover:
            # 先删后下载
            cover_path = f"{read_config('image_dir')}/masiro/{book.book_id}"
            if os.path.isdir(cover_path):
                for file_name in os.listdir(cover_path):
                    file_path = os.path.join(cover_path, file_name)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
            # 下载封面
            cover_url = f"{self.domain}{book.cover_url}" if book.cover_url.startswith("/images") else book.cover_url
            await request.download_pic(cover_url, self.pic_header, cover_path, self.session)

    async def build_chapter_list(self, book: Book):
        if not book.chapter_xpaths:
            return
        # 数据库已存章节
        old_chapters = await get_chapter_list(book.id)
        chapters = []
        order = 1
        parent_chapter_json = json.loads(common.first(common.get_xpath(book.page_text, "masiro", "parent_chapter")))
        chapter_json = json.loads(common.first(common.get_xpath(book.page_text, "masiro", "chapter")))
        if not parent_chapter_json or not chapter_json:
            log.debug(book.page_text)
            return
        for parent_chapter in parent_chapter_json:
            for chapter_data in chapter_json:
                if chapter_data["parent_id"] != parent_chapter["id"]:
                    continue
                chapter_id = str(chapter_data["id"])
                chapter_name = chapter_data["title"]
                last_update_time = common.get_timestamp(chapter_data["episode_update_time"])
                # 匹配数据库已存章节
                chapter = common.find(old_chapters, "chapter_id", chapter_id)
                if chapter:
                    chapter.book_id = book.book_id
                    chapter.pics = []
                    chapter.cost = chapter_data["cost"]
                    if chapter.chapter_order != order or chapter.chapter_name != chapter_name:
                        # 标题或顺序改变 更新数据库
                        chapter.chapter_order = order
                        chapter.chapter_name = chapter_name
                        await update_chapter(chapter)
                    if (chapter.purchase_fail_flag and chapter.purchase_fail_flag == 1
                            and read_config("is_purchase") and chapter_data["cost"] <= read_config("max_purchase")):
                        # 打钱失败的 重新打钱并更新数据库
                        await self.build_content(chapter)
                        await update_chapter(chapter)
                    if chapter.last_update_time < last_update_time:
                        # 章节有更新 重新爬取文本并更新数据库
                        chapter.last_update_time = last_update_time
                        await self.build_content(chapter)
                        await update_chapter(chapter)
                else:
                    # 新章节
                    chapter = Chapter()
                    chapter.chapter_order = order
                    chapter.book_table_id = book.id
                    chapter.chapter_id = chapter_id
                    chapter.chapter_name = chapter_name
                    chapter.last_update_time = last_update_time
                    chapter.book_id = book.book_id
                    chapter.cost = chapter_data["cost"]
                    # 获取内容
                    await self.build_content(chapter)
                    # 更新数据库
                    await update_chapter(chapter)
                order += 1
                chapters.append(chapter)
        book.chapters = chapters

    async def build_content(self, chapter: Chapter):
        # todo 打钱
        log.info(f"{chapter.chapter_name} 真白萌开始获取章节内容...")
        url = f"{self.domain}/admin/novelReading?cid={chapter.chapter_id}"
        log.debug(url)
        text = await request.get(url, self.header, self.session)
        if not text:
            log.debug(url)
            return
        if chapter.cost > 0 and "立即打钱" in text:
            # 打钱
            chapter.purchase_fail_flag = 1
            if read_config("is_purchase") and chapter.cost <= read_config("max_purchase"):
                text = await self.pay(chapter)
                if not text:
                    log.debug(url)
                    return
        chapter.content = common.get_html(text, "masiro", "content")
        log.info(f"{chapter.chapter_name} 真白萌新获取章节内容")

    async def build_pic_list(self, chapter: Chapter):
        pic_urls = common.get_xpath(chapter.content, "masiro", "pic")
        if not pic_urls:
            return
        # 数据库已存图片列表
        pics = await get_pic_list(chapter.id)
        for pic_url in pic_urls:
            if not pic_url.startswith("http"):
                return
            save_path = f"{read_config('image_dir')}/masiro/{chapter.book_id}/{chapter.chapter_id}"
            # 匹配数据库
            pic = common.find(pics, "pic_url", pic_url)
            if pic:
                if not pic.pic_path:
                    # 下载图片
                    if pic_url.startswith("/images"):
                        pic_url = f"{self.domain}/{pic_url}"
                    pic_path = await request.download_pic(pic_url, self.pic_header, save_path, self.session)
                    if pic_path:
                        pic.pic_path = pic_path
                        # 数据库更新图片保存路径
                        await update_pic(pic)
            else:
                pic = Pic()
                pic.pic_url = pic_url
                pic.chapter_table_id = chapter.id
                if pic_url.startswith("/images"):
                    pic_url = f"{self.domain}/{pic_url}"
                # 下载图片
                pic_path = await request.download_pic(pic_url, self.pic_header, save_path, self.session)
                if pic_path:
                    pic.pic_path = pic_path
                # 数据库新增图片信息
                await insert_pic(pic)
            chapter.pics.append(pic)

    async def fuck_cf(self) -> bool:
        log.info("真白萌开始破cf盾...")
        url = read_config("login_info")["masiro"]["flaresolverr_url"]
        data = {
            "cmd": "request.get",
            "url": f"{self.domain}/admin/auth/login",
            "maxTimeout": 60000
        }
        res = await request.post_json(url, {"content-type": "application/json"}, data, self.session)
        if res:
            res_json = json.loads(res)
            self.header["User-Agent"] = res_json["solution"]["userAgent"]
            for cf_cookie in res_json["solution"]["cookies"]:
                if cf_cookie["name"] == "cf_clearance":
                    self.header["Cookie"] = f"cf_clearance={cf_cookie['value']};"
                    log.info("真白萌破cf盾成功！")
                    return True
        return False

    async def get_token(self, url: str):
        res = await request.get(url, self.header, self.session)
        if res:
            self.token = common.first(common.get_xpath(res, "masiro", "token"))

    async def pay(self, chapter: Chapter) -> str:
        log.info(f"真白萌开始打钱..花费:{chapter.cost}金币")
        cost_param = {
            "type": 2,
            "object_id": chapter.chapter_id,
            "cost": chapter.cost
        }
        cost_header = copy.deepcopy(self.header)
        cost_header['x-csrf-token'] = self.token
        cost_res = await request.post_json(f"{self.domain}/admin/pay", self.header, cost_param, self.session)
        if cost_res and json.loads(cost_res)["code"] == 1:
            chapter.purchase_fail_flag = 0
            # 打钱成功 刷新文本
            log.info(f"{chapter.chapter_name} 真白萌打钱成功！")
            url = f"{self.domain}/admin/novelReading?cid={chapter.chapter_id}"
            text = await request.get(url, self.header, self.session)
            return text
        log.info(f"{chapter.chapter_name} 真白萌打钱失败")
        return None