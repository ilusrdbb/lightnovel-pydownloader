import json
import os
import re

from aiohttp import ClientSession
from lxml import html

from src.db.book import update_book
from src.db.chapter import get_chapter_list, update_chapter
from src.db.cookie import update_cookie
from src.db.pic import update_pic, insert_pic, get_pic_list
from src.models.book import Book
from src.models.chapter import Chapter
from src.models.cookie import Cookie
from src.models.pic import Pic
from src.sites.base import BaseSite
from src.utils import request, common
from src.utils.config import read_config
from src.utils.log import log


class Esj(BaseSite):

    def __init__(self, session: ClientSession):
        super().__init__(session)
        self.site: str = "esj"
        self.domain: str = read_config("domain")["esj"]

    async def valid_cookie(self) -> bool:
        url = f"{self.domain}/my/profile"
        res = await request.get(url, self.header, self.session)
        if res and "list-11" in res:
            log.info("esj校验cookie成功")
            return True
        log.info("esj cookie失效")
        log.debug(res)
        return False

    async def login(self):
        cookie = Cookie()
        cookie.source = "esj"
        if (not read_config("login_info")["esj"]["username"]
                or not read_config("login_info")["esj"]["password"]):
            if read_config("login_info")["esj"]["cookie"]:
                cookie.cookie = read_config("login_info")["esj"]["cookie"]
            else:
                raise Exception("esj未配置登录信息")
        else:
            url = f"{self.domain}/inc/mem_login.php"
            login_data = {
                "email": read_config("login_info")["esj"]["username"],
                "pwd": read_config("login_info")["esj"]["password"],
                "remember_me": "on"
            }
            res = await request.post_data(url, self.header, login_data, self.session)
            if res:
                if json.loads(res["text"])["status"] != 200:
                    log.debug(res)
                    raise Exception(f"esj登录失败 {json.loads(res['text'])['msg']}")
                cookie.cookie = ";".join(res["headers"].getall("Set-Cookie"))
            else:
                raise Exception("esj登录失败")
        # 再校验一次cookie
        self.cookie = cookie
        self.header["Cookie"] = cookie.cookie
        is_effective_cookie = await self.valid_cookie()
        if not is_effective_cookie:
            raise Exception("esj登录失败 cookie失效")
        # 数据库更新
        await update_cookie(cookie)

    async def get_book_list(self):
        # 白名单
        if read_config("white_list"):
            for white_book_id in common.handle_url_list(read_config("white_list"), "esj"):
                book = Book()
                book.source = "esj"
                book.book_id = white_book_id
                self.books.append(book)
            return
        # 正常爬取
        for page in range(self.start_page, self.end_page + 1):
            log.info(f"esj开始爬取第{page}页...")
            if read_config("get_collection"):
                url = f"{self.domain}/list-11/{page}.html"
            else:
                url = f"{self.domain}/my/favorite/{page}"
            res = await request.get(url, self.header, self.session)
            if not res:
                return
            if read_config("get_collection"):
                book_xpaths = common.get_xpath(res, "esj", "collection")
            else:
                book_xpaths = common.get_xpath(res, "esj", "page")
            if not book_xpaths:
                log.info("esj列表解析失败")
                log.debug(res)
                return
            for book_xpath in book_xpaths:
                book = Book()
                book.source = "esj"
                book.book_id = common.get_book_id(book_xpath, "esj")
                # 黑名单跳过
                if book.book_id in common.handle_url_list(read_config("black_list"), "esj"):
                    continue
                self.books.append(book)

    async def build_book_info(self, book: Book):
        url = f"{self.domain}/detail/{book.book_id}.html"
        res = await request.get(url, self.header, self.session)
        if not res:
            log.info(f"{url} esj获取书籍信息失败")
            return
        book.book_name = common.first(common.get_xpath(res, "esj", "title"))
        book.author = common.first(common.get_xpath(res, "esj", "author"))
        book.describe = common.join(common.get_xpath(res, "esj", "describe"), "\n")
        book.cover_url = common.first(common.get_xpath(res, "esj", "cover"))
        book.tags = common.join(common.get_xpath(res, "esj", "tags"))
        book.chapter_xpaths = common.get_xpath(res, "esj", "chapter")
        # 更新数据库
        download_cover = await update_book(book)
        if download_cover:
            # 先删后下载
            cover_path = f"{read_config('image_dir')}/esj/{book.book_id}"
            if os.path.isdir(cover_path):
                for file_name in os.listdir(cover_path):
                    file_path = os.path.join(cover_path, file_name)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
            # 下载封面
            await request.download_pic(book.cover_url, self.pic_header, cover_path, self.session)

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
            if not chapter_url or "esjzone" not in chapter_url:
                # 外站跳过
                log.info(f"esj检测到外站链接，跳过本章 {chapter_url}")
                continue
            chapter_id = None if not re.search(r"/(\d+)\.html", chapter_url) else re.search(r"/(\d+)\.html", chapter_url).group(1)
            if not chapter_id:
                log.info(f"esj章节地址配置错误，跳过本章 {chapter_url}")
                continue
            chapter_name = common.first(chapter_body.xpath("@data-title"))
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
        log.info(f"{chapter.chapter_name} esj开始获取章节内容...")
        url = f"{self.domain}/forum/{chapter.book_id}/{chapter.chapter_id}.html"
        text = await request.get(url, self.header, self.session)
        if not text:
            log.debug(url)
            return
        chapter.content = common.get_html(text, "esj", "content")
        if not chapter.content or "btn-send-pw" in chapter.content or "內文目前施工中" in chapter.content:
            # 密码章节跳过
            log.info(f"esj密码章节，跳过本章 {chapter.chapter_name}")
            return
        log.info(f"{chapter.chapter_name} esj新获取章节内容")

    async def build_pic_list(self, chapter: Chapter):
        pic_urls = common.get_xpath(chapter.content, "esj", "pic")
        if not pic_urls:
            return
        # 数据库已存图片列表
        pics = await get_pic_list(chapter.id)
        for pic_url in pic_urls:
            if not pic_url.startswith("http"):
                return
            save_path = f"{read_config('image_dir')}/esj/{chapter.book_id}/{chapter.chapter_id}"
            # 匹配数据库
            pic = common.find(pics, "pic_url", pic_url)
            if pic:
                if not pic.pic_path:
                    # 下载图片
                    pic_path = await request.download_pic(pic.pic_url, self.pic_header, save_path, self.session)
                    if pic_path:
                        pic.pic_path = pic_path
                        # 数据库更新图片保存路径
                        await update_pic(pic)
            else:
                pic = Pic()
                pic.pic_url = pic_url
                pic.chapter_table_id = chapter.id
                # 下载图片
                pic_path = await request.download_pic(pic.pic_url, self.pic_header, save_path, self.session)
                if pic_path:
                    pic.pic_path = pic_path
                # 数据库新增图片信息
                await insert_pic(pic)
            chapter.pics.append(pic)

    async def sign(self):
        pass