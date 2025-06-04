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


class Yuri(BaseSite):

    def __init__(self, session: ClientSession):
        super().__init__(session)
        self.site: str = "yuri"
        self.domain: str = read_config("domain")["yuri"]
        # 容易触发discuz反爬强制单线程
        self.threads = asyncio.Semaphore(1)

    async def valid_cookie(self) -> bool:
        url = f"{self.domain}/home.php?mod=spacecp&ac=usergroup"
        res = await request.get(url, self.header, self.session)
        if res and "<title>用户组" in res:
            log.info("百合会校验cookie成功")
            return True
        log.info("百合会cookie失效")
        log.debug(res)
        return False

    async def login(self):
        cookie = Cookie()
        cookie.source = "yuri"
        if not read_config("login_info")["yuri"]["cookie"]:
            raise Exception("百合会未配置登录信息")
        cookie.cookie = read_config("login_info")["yuri"]["cookie"]
        # 再校验一次cookie
        self.cookie = cookie
        self.header["Cookie"] = cookie.cookie
        is_effective_cookie = await self.valid_cookie()
        if not is_effective_cookie:
            raise Exception("百合会登录失败 cookie失效")
        # 数据库更新
        await update_cookie(cookie)

    async def get_book_list(self):
        # 白名单
        if read_config("white_list"):
            for white_book_id in common.handle_url_list(read_config("white_list"), "yuri"):
                book = Book()
                book.source = "yuri"
                book.book_id = white_book_id
                self.books.append(book)
            return
        # 正常爬取
        for page in range(self.start_page, self.end_page + 1):
            log.info(f"百合会开始爬取第{page}页...")
            if read_config("get_collection"):
                url = f"{self.domain}/home.php?mod=space&do=favorite&type=thread&page={page}"
            else:
                url = f"{self.domain}/forum-55-{page}.html"
            res = await request.get(url, self.header, self.session)
            if not res:
                return
            if read_config("get_collection"):
                book_urls = common.get_xpath(res, "yuri", "collection")
            else:
                book_urls = common.get_xpath(res, "yuri", "page")
            if not book_urls:
                log.info("百合会列表解析失败")
                log.debug(res)
                return
            for book_url in book_urls:
                if "javascript" in book_url or "thread-535989-" in book_url:
                    # 排除置顶专楼
                    continue
                book = Book()
                book.source = "yuri"
                book.book_id = common.get_book_id(book_url, "yuri")
                # 黑名单跳过
                if book.book_id in common.handle_url_list(read_config("black_list"), "yuri"):
                    continue
                self.books.append(book)

    async def build_book_info(self, book: Book):
        url = f"{self.domain}/thread-{book.book_id}-1-1.html"
        res = await self.handle_dsign(url)
        if not res:
            log.info(f"{url} 百合会获取书籍信息失败")
            return
        book.book_name = common.first(common.get_xpath(res, "yuri", "title"))
        # 临时存储楼主id 用于只看楼主
        book.author = common.first(common.get_xpath(res, "yuri", "author"))
        # 更新数据库
        await update_book(book)

    async def build_chapter_list(self, book: Book):
        # 获取全部楼主楼层的文本
        content_list = await self.get_content_list(book)
        if not content_list:
            return
        # 数据库已存章节
        old_chapters = await get_chapter_list(book.id)
        chapters = []
        order = 1
        for content in content_list:
            chapter_name = str(order)
            chapter_id = str(order)
            # 匹配数据库已存章节
            chapter = common.find(old_chapters, "chapter_id", chapter_id)
            if chapter:
                chapter.book_id = book.book_id
                chapter.pics = []
                # 无脑更新
                chapter.content = content
                await update_chapter(chapter)
            else:
                # 新章节
                chapter = Chapter()
                chapter.chapter_order = order
                chapter.book_table_id = book.id
                chapter.chapter_id = chapter_id
                chapter.chapter_name = chapter_name
                chapter.book_id = book.book_id
                chapter.content = content
                # 更新数据库
                await update_chapter(chapter)
            order += 1
            chapters.append(chapter)
        book.chapters = chapters

    async def build_content(self, chapter: Chapter):
        pass

    async def build_pic_list(self, chapter: Chapter):
        pic_urls = common.get_xpath(chapter.content, "yuri", "pic")
        if not pic_urls:
            return
        # 数据库已存图片列表
        pics = await get_pic_list(chapter.id)
        for pic_url in pic_urls:
            save_path = f"{read_config('image_dir')}/yuri/{chapter.book_id}/{chapter.chapter_id}"
            # 匹配数据库
            pic = common.find(pics, "pic_url", pic_url)
            if pic:
                if not pic.pic_path:
                    # 下载图片
                    if not pic_url.startswith("http"):
                        # 论坛自己的图床
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
                if not pic_url.startswith("http"):
                    pic_url = f"{self.domain}/{pic_url}"
                # 下载图片
                pic_path = await request.download_pic(pic_url, self.pic_header, save_path, self.session)
                if pic_path:
                    pic.pic_path = pic_path
                # 数据库新增图片信息
                await insert_pic(pic)
            chapter.pics.append(pic)

    async def sign(self):
        log.info("百合会开始签到...")
        hash_url = f"{self.domain}/plugin.php?id=zqlj_sign"
        hash_res = await request.get(hash_url, headers=self.header, session=self.session)
        if not hash_res:
            log.info("百合会签到失败！")
            return
        form_hash = common.first(common.get_xpath(hash_res, "yuri", "sign"))
        if not form_hash:
            log.debug(hash_res)
            log.info("百合会签到失败！")
            return
        sign_url = f"{self.domain}/plugin.php?id=zqlj_sign&sign={form_hash}"
        sign_res = await request.get(sign_url, self.header, self.session)
        if not sign_res:
            log.info("百合会签到失败！")
            return
        log.debug(sign_res)
        log.info("百合会签到成功！")

    async def handle_dsign(self, url: str) -> str:
        _url = url
        res = await request.get(url, self.header, self.session)
        if res.startswith("<script"):
            # 反爬处理
            _url = f"{self.domain}{get_dsign(res)}"
            res = await request.get(_url, self.header, self.session)
        return res

    async def get_content_list(self, book: Book) -> List[str]:
        # 只看楼主
        first_page_url = f"{self.domain}/forum.php?mod=viewthread&tid={book.book_id}&page=1&authorid={book.author}"
        first_page_res = await self.handle_dsign(first_page_url)
        if not first_page_res:
            return None
        log.info(f"{book.book_name} 百合会开始获取书籍内容...")
        content_list = self.get_contents_from_res(first_page_res)
        # 获取页数
        page_size_xpath = common.first(common.get_xpath(first_page_res, "yuri", "size"))
        if not page_size_xpath:
            page_size = 1
        else:
            page_size = int(re.findall("\d+", page_size_xpath)[0])
        if page_size == 1:
            log.info(f"{book.book_name} 百合会已获取书籍内容")
            return content_list
        for page in range(2, page_size + 1):
            other_page_url = f"{self.domain}/forum.php?mod=viewthread&tid={book.book_id}&page={page}&authorid={book.author}"
            other_page_res = await self.handle_dsign(other_page_url)
            if not other_page_res:
                continue
            content_list += self.get_contents_from_res(other_page_res)
        log.info(f"{book.book_name} 百合会已获取书籍内容")
        return content_list

    @staticmethod
    def get_contents_from_res(res: str) -> List[str]:
        result_list = []
        content_xpaths = common.get_xpath(res, "yuri", "chapter")
        if not content_xpaths:
            return result_list
        for content_xpath in content_xpaths:
            content = html.tostring(content_xpath, pretty_print=True, encoding="unicode")
            result_list.append(content)
        return result_list

