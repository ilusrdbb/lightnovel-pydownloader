import copy
import os
import random
from typing import Dict, List, Any

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


class LK(BaseSite):

    def __init__(self, session: ClientSession):
        super().__init__(session)
        self.site: str = "lk"
        self.domain: str = read_config("domain")["lk"]
        self.header = {
            "content-type": "application/json; charset=UTF-8",
            "accept-encoding": "gzip",
            "host": self.domain.replace("https://", ""),
            "user-agent": "Dart/2.10 (dart:io)"
        }
        self.pic_header["referer"] = f"{self.domain}/".replace("api.", "www.")
        self.param: Dict[str, Any] = {
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
        # 记录轻币和经验
        self.user_info: Dict[str, int] = {}
        self.sign_url: str = f"{self.domain}/api/task/complete"

    async def valid_cookie(self) -> bool:
        url = f"{self.domain}/api/user/info"
        self.param["d"]["uid"] = self.cookie.uid
        self.param["d"]["security_key"] = self.cookie.token
        res = await request.post_json(url, self.header, self.param, self.session)
        if res and common.unzip(res).get("code") == 0:
            log.info("轻国校验cookie成功")
            self.user_info["coin"] = common.unzip(res)["data"]["balance"]["coin"]
            self.user_info["exp"] = common.unzip(res)["data"]["level"]["exp"]
            return True
        log.info("轻国 cookie失效")
        log.debug(common.unzip(res))
        return False

    async def login(self):
        cookie = Cookie()
        cookie.source = "lk"
        if (not read_config("login_info")["lk"]["username"]
                or not read_config("login_info")["lk"]["password"]):
            raise Exception("轻国未配置登录信息")
        else:
            url = f"{self.domain}/api/user/login"
            login_data = copy.deepcopy(self.param)
            login_data["is_encrypted"] = 0
            login_data["d"] = {
                "username": read_config("login_info")["lk"]["username"],
                "password": read_config("login_info")["lk"]["password"]
            }
            res = await request.post_json(url, self.header, login_data, self.session)
            if res and common.unzip(res)["code"] == 0:
                cookie.uid = common.unzip(res)["data"]["uid"]
                cookie.token = common.unzip(res)["data"]["security_key"]
                self.param["d"]["uid"] = cookie.uid
                self.param["d"]["security_key"] = cookie.token
            else:
                raise Exception("轻国登录失败")
        # 再校验一次cookie
        self.cookie = cookie
        is_effective_cookie = await self.valid_cookie()
        if not is_effective_cookie:
            raise Exception("轻国登录失败 cookie失效")
        # 数据库更新
        await update_cookie(cookie)

    async def get_book_list(self):
        page_param = copy.deepcopy(self.param)
        # 白名单
        if read_config("white_list"):
            for white_book_id in common.handle_url_list(read_config("white_list"), "lk"):
                book = Book()
                book.source = "lk"
                book.book_id = white_book_id
                self.books.append(book)
            return
        # 收藏单本或列表页面
        for page in range(self.start_page, self.end_page + 1):
            log.info(f"轻国开始爬取第{page}页...")
            if read_config("get_collection"):
                url = f"{self.domain}/api/history/get-collections"
                page_param["d"]["type"] = 1
                page_param["d"]["class"] = 1
            else:
                url = f"{self.domain}/my/favorite/{page}"
                page_param["d"]["parent_gid"] = 3
                # gid 106 最新 gid 107 整卷
                page_param["d"]["gid"] = 106
            res = await request.post_json(url, self.header, page_param, self.session)
            if not res or common.unzip(res)["code"] != 0:
                log.debug(page_param)
                log.debug(common.unzip(res))
                return
            book_list = common.unzip(res)["data"]["list"]
            for book_data in book_list:
                book = Book()
                book.source = "lk"
                book.book_id = str(book_data["aid"]) if book_data["sid"] == 0 else str(book_data["sid"])
                book.book_name = book_data["title"]
                book.cover_url = book_data["cover"]
                # 黑名单跳过
                if book.book_id in common.handle_url_list(read_config("black_list"), "lk"):
                    continue
                # 官方置顶
                if book.book_id in ["969547", "1113228", "1099310", "1048596"]:
                    continue
                self.books.append(book)
        # 收藏合集
        for page in range(self.start_page, self.end_page + 1):
            if read_config("get_collection"):
                url = f"{self.domain}/api/history/get-collections"
                page_param["d"]["type"] = 1
                page_param["d"]["class"] = 2
                res = await request.post_json(url, self.header, page_param, self.session)
                if not res or common.unzip(res)["code"] != 0:
                    log.debug(page_param)
                    log.debug(common.unzip(res))
                    return
                book_list = common.unzip(res)["data"]["list"]
                for book_data in book_list:
                    book = Book()
                    book.source = "lk"
                    book.book_id = str(book_data["sid"])
                    if book.book_id in common.handle_url_list(read_config("black_list"), "lk"):
                        continue
                    self.books.append(book)

    async def build_book_info(self, book: Book):
        book_param = copy.deepcopy(self.param)
        if int(book.book_id) < 100000:
            # 合集
            url = f"{self.domain}/api/series/get-info"
            book_param["d"]["sid"] = book.book_id
            res = await request.post_json(url, self.header, book_param, self.session)
            if not res or common.unzip(res)["code"] != 0:
                log.debug(book_param)
                log.debug(common.unzip(res))
                log.info(f"{book.book_id} 轻国获取书籍信息失败")
                return
            book_dict = common.unzip(res)["data"]
            book.book_name = book_dict["name"]
            book.author = book_dict["author"]
            book.cover_url = book_dict["cover"]
            book.describe = book_dict["intro"]
            book.chapter_datas = book_dict["articles"]
        else:
            # 单本
            url = f"{self.domain}/api/article/get-detail"
            book_param["d"]["aid"] = book.book_id
            book_param["d"]["simple"] = 0
            res = await request.post_json(url, self.header, book_param, self.session)
            if not res or common.unzip(res)["code"] != 0:
                log.debug(book_param)
                log.debug(common.unzip(res))
                log.info(f"{book.book_id} 轻国获取书籍信息失败")
                return
            book_dict = common.unzip(res)["data"]
            book.book_name = book_dict["title"]
            book.cover_url = book_dict["cover"]
            book.describe = book_dict["summary"]
            book.chapter_datas = [book_dict]
        # 更新数据库
        download_cover = await update_book(book)
        if download_cover:
            # 先删后下载
            cover_path = f"{read_config('image_dir')}/lk/{book.book_id}"
            if os.path.isdir(cover_path):
                for file_name in os.listdir(cover_path):
                    file_path = os.path.join(cover_path, file_name)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
            # 下载封面
            cover_url = book.cover_url.replace("lightnovel.us", self.domain.replace("https://api.", ""))
            await request.download_pic(cover_url, self.pic_header, cover_path, self.session)

    async def build_chapter_list(self, book: Book):
        # 数据库已存章节
        old_chapters = await get_chapter_list(book.id)
        chapters = []
        order = 1
        for chapter_data in book.chapter_datas:
            chapter_id = str(chapter_data["aid"])
            chapter_name = chapter_data["title"]
            last_update_time =  common.get_timestamp(chapter_data["time"])
            # 匹配数据库已存章节
            chapter = common.find(old_chapters, "chapter_id", chapter_id)
            if chapter:
                chapter.book_id = book.book_id
                chapter.pics = []
                chapter.pic_datas = []
                if chapter.chapter_order != order or chapter.chapter_name != chapter_name:
                    # 标题或顺序改变 更新数据库
                    chapter.chapter_order = order
                    chapter.chapter_name = chapter_name
                    await update_chapter(chapter)
                if chapter.purchase_fail_flag and chapter.purchase_fail_flag == 1 and read_config("is_purchase"):
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
                # 获取内容
                await self.build_content(chapter)
                # 更新数据库
                await update_chapter(chapter)
            order += 1
            chapters.append(chapter)
        book.chapters = chapters

    async def build_content(self, chapter: Chapter):
        log.info(f"{chapter.chapter_name} 轻国开始获取章节内容...")
        # 构造图片列表
        pic_datas = []
        chapter_param = copy.deepcopy(self.param)
        url = f"{self.domain}/api/article/get-detail"
        chapter_param["d"]["aid"] = chapter.chapter_id
        chapter_param["d"]["simple"] = 0
        res = await request.post_json(url, self.header, chapter_param, self.session)
        if not res or common.unzip(res)["code"] != 0:
            log.debug(chapter_param)
            log.debug(common.unzip(res))
            return
        chapter_dict = common.unzip(res)["data"]
        if chapter_dict.get("pay_info"):
            # 打钱处理
            if chapter_dict.get("pay_info")["is_paid"] == 0 and read_config("is_purchase"):
                chapter.purchase_fail_flag = 1
                cost = chapter_dict.get("pay_info")["price"]
                if cost <= read_config("max_purchase"):
                    await self.pay(chapter, cost, pic_datas)
            elif chapter_dict.get("pay_info")["is_paid"] == 1:
                # 已经打过钱了正常获取章节内容
                chapter.purchase_fail_flag = 0
                chapter.content = common.bbcode_to_html(chapter_dict["content"], chapter_dict, pic_datas)
            else:
                chapter.purchase_fail_flag = 1
        else:
            chapter.content = common.bbcode_to_html(chapter_dict["content"], chapter_dict, pic_datas)
        chapter.pic_datas = pic_datas
        log.info(f"{chapter.chapter_name} 轻国新获取章节内容")

    async def build_pic_list(self, chapter: Chapter):
        # 数据库已存图片列表
        pics = await get_pic_list(chapter.id)
        if pics:
            for pic in pics:
                if pic.pic_path:
                    chapter.pics.append(pic)
                else:
                    # 下载图片
                    save_path = f"{read_config('image_dir')}/lk/{chapter.book_id}/{chapter.chapter_id}"
                    # 旧域名处理
                    pic_url = pic.pic_url.replace("lightnovel.us", self.domain.replace("https://api.", ""))
                    pic_path = await request.download_pic(pic_url, self.pic_header, save_path, self.session)
                    if pic_path:
                        pic.pic_path = pic_path
                        # 更新数据库
                        await update_pic(pic)
                chapter.pics.append(pic)
        if not chapter.pic_datas:
            return
        for pic_data in chapter.pic_datas:
            # 匹配数据库
            pic = common.find(pics, "pic_url", pic_data["url"])
            if pic:
                continue
            # 新图片
            pic = Pic()
            pic.pic_url = pic_data["url"]
            pic.pic_id = pic_data["id"]
            pic.chapter_table_id = chapter.id
            # 下载图片
            save_path = f"{read_config('image_dir')}/lk/{chapter.book_id}/{chapter.chapter_id}"
            # 旧域名处理
            pic_url = pic_data["url"].replace("lightnovel.us", self.domain.replace("https://api.", ""))
            pic_path = await request.download_pic(pic_url, self.pic_header, save_path, self.session)
            if pic_path:
                pic.pic_path = pic_path
            # 数据库新增图片信息
            await insert_pic(pic)
            chapter.pics.append(pic)

    async def pay(self, chapter: Chapter, cost: int, pic_urls: List[Dict[str, str]]):
        log.info(f"{chapter.chapter_name} 轻国开始打钱...花费:{cost}轻币")
        cost_url = f"{self.domain}/api/coin/use"
        cost_param = copy.deepcopy(self.param)
        cost_param["d"]["goods_id"] = 1
        cost_param["d"]["params"] = int(chapter.chapter_id)
        cost_param["d"]["price"] = cost
        cost_param["d"]["number"] = 1
        cost_param["d"]["total_price"] = cost
        cost_res = await request.post_json(cost_url, self.header, cost_param, self.session)
        if cost_res and common.unzip(cost_res)["code"] == 0:
            chapter.purchase_fail_flag = 0
            # 打钱成功 刷新文本
            log.info(f"{chapter.chapter_name} 轻国打钱成功！")
            url = f"{self.domain}/api/article/get-detail"
            chapter_param = copy.deepcopy(self.param)
            chapter_param["d"]["aid"] = chapter.chapter_id
            chapter_param["d"]["simple"] = 0
            res = await request.post_json(url, self.header, chapter_param, self.session)
            if not res or common.unzip(res)["code"] != 0:
                log.debug(chapter_param)
                log.debug(common.unzip(res))
                return
            chapter_dict = common.unzip(res)["data"]
            chapter.content = common.bbcode_to_html(chapter_dict["content"], chapter_dict, pic_urls)
        else:
            log.info(f"{chapter.chapter_name} 轻国打钱失败！")

    async def sign(self):
        log.info("轻国开始签到...")
        log.info(f"轻币：{self.user_info['coin']} 经验：{self.user_info['exp']}")
        param = copy.deepcopy(self.param)
        # 登录签到
        sign_url = f"{self.domain}/api/task/complete"
        sign_res = await request.post_json(sign_url, self.header, param, self.session)
        if not sign_res:
            log.info("轻国签到失败！")
            return
        sign_res = common.unzip(sign_res)
        log.debug(sign_res)
        # 获取个人任务
        task_url = f"{self.domain}/api/task/list"
        task_res = await request.post_json(task_url, self.header, param, self.session)
        if not task_res:
            log.info("轻国签到失败！")
            return
        task_list = common.unzip(task_res)
        log.debug(task_list)
        # 阅读任务
        read_url = f"{self.domain}/api/history/add-history"
        param["d"]["fid"] = 2408
        param["d"]["class"] = 2
        param["d"]["id"] = 1
        await request.post_json(read_url, self.header, param, self.session)
        task_param = copy.deepcopy(self.param)
        task_param["d"]["id"] = 1
        read_res = await request.post_json(self.sign_url, self.header, task_param, self.session)
        log.debug(common.unzip(read_res))
        log.info("阅读任务成功！") if read_res else log.info("阅读任务失败！")
        # 收藏任务
        if task_list["data"]["items"][1]["status"] == 0:
            collection_url = f"{self.domain}/api/history/add-collection"
            param["d"]["fid"] = 1123305
            param["d"]["class"] = 1
            param["d"]["id"] = 2
            await request.post_json(collection_url, self.header, param, self.session)
            task_param = copy.deepcopy(self.param)
            task_param["d"]["id"] = 2
            collection_res = await request.post_json(self.sign_url, self.header, task_param, self.session)
            log.debug(common.unzip(collection_res))
            log.info("收藏任务成功！") if collection_res else log.info("收藏任务失败！")
        # 点赞任务
        if task_list["data"]["items"][2]["status"] == 0:
            await self.sign_like()
        # 分享任务
        if task_list["data"]["items"][3]["status"] == 0:
            task_param = copy.deepcopy(self.param)
            task_param["d"]["id"] = 5
            share_res = await request.post_json(self.sign_url, self.header, task_param, self.session)
            log.debug(common.unzip(share_res))
            log.info("分享任务成功！") if share_res else log.info("分享任务失败！")
        # 投币任务
        if task_list["data"]["items"][4]["status"] == 0:
            await self.sign_pay()
        # 全部完成
        if task_list["data"]["status"] == 0:
            task_param = copy.deepcopy(self.param)
            task_param["d"]["id"] = 7
            final_res = await request.post_json(self.sign_url, self.header, task_param, self.session)
            log.debug(common.unzip(final_res))
            log.info("全部任务成功！") if final_res else log.info("全部任务失败！")
        else:
            log.info("已完成全部任务！")
        # 刷新
        self.valid_cookie()
        log.info("轻国签到成功！")
        log.info(f"轻币：{self.user_info['coin']} 经验：{self.user_info['exp']}")

    async def sign_like(self, retry_time: int = 0):
        # 点赞
        random_aid = random.randint(1000000, 1125000)
        like_url = f"{self.domain}/api/article/like"
        like_param = copy.deepcopy(self.param)
        like_param["d"]["aid"] = random_aid
        like_param["d"]["id"] = 3
        # 执行两次 取消点赞
        await request.post_json(like_url, self.header, like_param, self.session)
        await request.post_json(like_url, self.header, like_param, self.session)
        # 任务
        task_param = copy.deepcopy(self.param)
        task_param["d"]["id"] = 3
        res = await request.post_json(self.sign_url, self.header, task_param, self.session)
        if not res or common.unzip(res)["code"] != 0:
            log.info("点赞任务失败！重试...")
            retry_time += 1
            if retry_time < 3:
                await self.sign_like(retry_time)
            return
        log.info("点赞任务成功！")

    async def sign_pay(self, retry_time: int = 0):
        # 投币
        random_aid = random.randint(1000000, 1125000)
        coin_url = f"{self.domain}/api/coin/use"
        coin_param = copy.deepcopy(self.param)
        coin_param["d"]["goods_id"] = 2
        coin_param["d"]["params"] = random_aid
        coin_param["d"]["price"] = 1
        coin_param["d"]["number"] = 10
        coin_param["d"]["total_price"] = 10
        await request.post_json(coin_url, self.header, coin_param, self.session)
        # 任务
        task_param = copy.deepcopy(self.param)
        task_param["d"]["id"] = 6
        res = await request.post_json(self.sign_url, self.header, task_param, self.session)
        if not res or common.unzip(res)["code"] != 0:
            log.info("投币任务失败！重试...")
            retry_time += 1
            if retry_time < 3:
                await self.sign_like(retry_time)
            return
        log.info("投币任务成功！")