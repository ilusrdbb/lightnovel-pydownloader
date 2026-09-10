import copy
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any

from aiohttp import ClientSession

from src.db.book import update_book
from src.db.chapter import get_chapter_list, update_chapter
from src.db.cookie import update_cookie
from src.db.pic import get_pic_list, insert_pic, update_pic
from src.models.book import Book
from src.models.chapter import Chapter
from src.models.cookie import Cookie
from src.models.pic import Pic
from src.sites.base import BaseSite
from src.utils import common, request
from src.utils.config import read_config
from src.utils.log import log


class LK2(BaseSite):

    def __init__(self, session: ClientSession):
        super().__init__(session)
        self.site: str = "lk2"
        self.domain: str = read_config("domain")["lk"]
        self.header = {
            "content-type": "application/json",
            "user-agent": "Dart/3.11 (dart:io)"
        }
        self.param: dict[str, Any] = {
            "is_encrypted": 0,
            "platform": "android",
            "client": "app",
            "gz": 0,
            "d": {
                "security_key": ""
            }
        }
        # 记录轻币和经验
        self.user_info: dict[str, int] = {}

    async def valid_cookie(self) -> bool:
        url = f"{self.domain}/proxy/api/bff/auth-session-v1"
        self.param["d"]["security_key"] = self.cookie.token
        res = await request.post_json(url, self.header, self.param, self.session)
        if res and json.loads(res).get("code") == 0 and json.loads(res)["data"]["logged_in"] == 1:
            self.user_info["coin"] = json.loads(res)["data"]["user"]["balance"]["coin"]
            self.user_info["exp"] = json.loads(res)["data"]["user"]["level"]["exp"]
            return True
        log.info("轻国登录失效")
        log.debug(json.loads(res))
        return False

    async def login(self):
        cookie = Cookie()
        cookie.source = "lk2"
        if (not read_config("login_info")["lk"]["username"]
                or not read_config("login_info")["lk"]["password"]):
            raise Exception("轻国未配置登录信息")
        else:
            url = f"{self.domain}/proxy/api/bff/auth-password-login-v1"
            login_data = {"d": {
                "username": read_config("login_info")["lk"]["username"],
                "password": read_config("login_info")["lk"]["password"]
            }}
            res = await request.post_json(url, self.header, login_data, self.session)
            if res and json.loads(res)["code"] == 0:
                cookie.uid = json.loads(res)["data"]["auth"]["uid"]
                cookie.token = json.loads(res)["data"]["auth"]["security_key"]
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
            for white_book_id in common.handle_url_list(read_config("white_list"), "lk2"):
                book = Book()
                book.source = "lk2"
                book.book_id = white_book_id
                self.books.append(book)
            return
        # 目前轻国全部为合集 没有单本
        for page in range(self.start_page, self.end_page + 1):
            log.info(f"轻国开始爬取第{page}页...")
            page_param["d"]["page_size"] = 20
            if read_config("get_collection"):
                page_param["d"]["page"] = page
                url = f"{self.domain}/proxy/api/bff/bookshelf-v1"
            else:
                url = f"{self.domain}/proxy/api/bff/home-lightnovel-feed-v1"
                # 怎么从0开始 迷惑
                page_param["d"]["page"] = page - 1
            res = await request.post_json(url, self.header, page_param, self.session)
            if not res or json.loads(res)["code"] != 0:
                log.debug(page_param)
                log.debug(json.loads(res))
                return
            book_list = json.loads(res)["data"]["list"]
            for book_data in book_list:
                book = Book()
                book.source = "lk2"
                book.book_id = book_data["book_id"]
                # 黑名单跳过
                if book.book_id in common.handle_url_list(read_config("black_list"), "lk2"):
                    continue
                self.books.append(book)

    async def build_book_info(self, book: Book):
        book_param = copy.deepcopy(self.param)
        url = f"{self.domain}/proxy/api/new-content-read/get-book-detail"
        book_param["d"]["book_id"] = book.book_id
        res = await request.post_json(url, self.header, book_param, self.session)
        if not res or json.loads(res)["code"] != 0:
            log.debug(book_param)
            log.debug(json.loads(res))
            log.info(f"{book.book_id} 轻国获取书籍信息失败")
            return
        book_dict = json.loads(res)["data"]
        book.book_name = book_dict["title"]
        book.author = book_dict["author_name"]
        book.cover_url = book_dict["cover_url"]
        book.tags = common.join(book_dict["tags"])
        book.describe = book_dict["summary"]
        book.volume_datas = book_dict["volumes"]
        # 更新数据库
        download_cover = await update_book(book)
        if download_cover:
            # 先删后下载
            cover_path = f"{read_config('image_dir')}/lk2/{book.book_id}"
            if os.path.isdir(cover_path):
                for file_name in os.listdir(cover_path):
                    file_path = os.path.join(cover_path, file_name)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
            # 下载封面
            cover_url = book.cover_url
            # 绕cf
            pic_header = copy.deepcopy(self.pic_header)
            await request.download_pic(cover_url, pic_header, cover_path, self.session, self.param)

    async def build_chapter_list(self, book: Book):
        # 数据库已存章节
        old_chapters = await get_chapter_list(book.id)
        chapters = []
        order = 1
        for volume_data in book.volume_datas:
            # 新轻国结构 书籍-卷-章节 先遍历卷再获取章节
            volume_param = copy.deepcopy(self.param)
            volume_url = f"{self.domain}/proxy/api/new-content-read/get-volume-chapters"
            volume_param["d"]["book_id"] = book.book_id
            volume_param["d"]["volume_id"] = volume_data["volume_id"]
            volume_param["d"]["page"] = 1
            volume_param["d"]["page_size"] = 50
            volume_res = await request.post_json(volume_url, self.header, volume_param, self.session)
            if not volume_res or json.loads(volume_res)["code"] != 0:
                log.debug(volume_param)
                log.debug(json.loads(volume_res))
                log.info(f"{book.book_id} 轻国获取卷失败")
                return
            # 可能有空章节的卷
            chapter_datas = json.loads(volume_res)["data"]["list"]
            if not chapter_datas:
                continue
            # 获取卷下章节接口有50条限制 需要先获取页数再遍历
            page_size = json.loads(volume_res)["data"]["pagination"]["page_count"]
            for page in range(1, page_size + 1):
                if page > 1:
                    volume_param["d"]["page"] = page
                    volume_page_res = await request.post_json(volume_url, self.header, volume_param, self.session)
                    chapter_datas = json.loads(volume_page_res)["data"]["list"]
                for chapter_data in chapter_datas:
                    chapter_id = str(chapter_data["chapter_id"])
                    chapter_name = chapter_data["title"]
                    last_update_time = common.get_timestamp(chapter_data["published_at"])
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
                        if chapter.last_update_time < last_update_time or not chapter.content:
                            # 章节有更新或之前爬取章节失败 重新爬取文本并更新数据库
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
        chapter_param = copy.deepcopy(self.param)
        url = f"{self.domain}/proxy/api/new-content-read/get-chapter-detail"
        chapter_param["d"]["book_id"] = chapter.book_id
        chapter_param["d"]["chapter_id"] = chapter.chapter_id
        chapter_param["d"]["with_body"] = 1
        res = await request.post_json(url, self.header, chapter_param, self.session)
        if not res or json.loads(res)["code"] != 0:
            log.debug(chapter_param)
            log.debug(json.loads(res))
            return
        chapter_dict = json.loads(res)["data"]
        # todo 暂时不考虑打钱
        # 回归传统的html 终于摆脱傻逼bbcode了
        chapter.content = chapter_dict["body_snapshot"]["body_html"]
        log.info(f"{chapter.chapter_name} 轻国新获取章节内容")

    async def build_pic_list(self, chapter: Chapter):
        # 直接借用esj的xpath了 反正是通用的
        pic_urls = common.get_xpath(chapter.content, "esj", "pic")
        if not pic_urls:
            return
        # 数据库已存图片列表
        pics = await get_pic_list(chapter.id)
        for pic_url in pic_urls:
            if not pic_url.startswith("http"):
                continue
            save_path = f"{read_config('image_dir')}/lk2/{chapter.book_id}/{chapter.chapter_id}"
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
        log.info("轻国开始签到...")
        log.info(f"轻币：{self.user_info['coin']} 经验：{self.user_info['exp']}")
        # 任务列表
        task_url = f"{self.domain}/proxy/api/bff/welfare-home-v1"
        task_res = await request.post_json(task_url, self.header, self.param, self.session)
        if not task_res or json.loads(task_res)["code"] != 0:
            log.info("轻国获取任务列表失败！")
            return
        task_list = json.loads(task_res)["data"]
        log.debug(task_list)
        # 每日签到
        if task_list["sign_in"]["enabled"] == 1 and task_list["sign_in"]["claimed"] == 0:
            await self.complete_sign()
        # 浏览任务
        view_task = next((item for item in task_list["tasks"]["items_preview"] if item["task_id"] == 300001), None)
        if view_task and (view_task["status"] == "in_progress" or view_task["status"] == "claimable"):
            # 新增浏览
            view_path = "/api/new-content-read/save-book-history"
            view_url = f"{self.domain}/proxy{view_path}"
            view_param = copy.deepcopy(self.param)
            view_param["d"]["book_id"] = 31605
            view_param["d"]["chapter_id"] = 317935
            view_param["d"]["last_position"] = 0
            view_param["d"]["progress_percent"] = 3
            view_param["d"]["volume_id"] = 46120
            fill_param_sign(view_param, view_path, True)
            view_res = await request.post_json(view_url, self.header, view_param, self.session)
            log.debug(view_res)
            # 完成浏览任务
            await self.complete_task(300001)
        # 收藏任务
        collect_task = next((item for item in task_list["tasks"]["items_preview"] if item["task_id"] == 300002), None)
        if collect_task and (collect_task["status"] == "in_progress" or collect_task["status"] == "claimable"):
            # 新增收藏
            await self.handle_collection(101, True)
            # 完成收藏任务
            await self.complete_task(300002)
            # 删除收藏
            await self.handle_collection(101, False)
        # 睡觉任务
        sleep_task = next((item for item in task_list["tasks"]["items_preview"] if item["task_id"] == 300003), None)
        if sleep_task:
            if sleep_task["status"] == "in_progress" and sleep_task.get("button_text") == "开始睡觉":
                # 接睡觉任务
                await self.start_sleep()
            if sleep_task["status"] == "claimable":
                # 完成睡觉任务
                await self.complete_task(300003)

    async def handle_collection(self, book_id: int, is_add: bool):
        param = copy.deepcopy(self.param)
        path = "/api/new-content-read/toggle-book-shelf"
        url = f"{self.domain}/proxy{path}"
        param["d"]["book_id"] = book_id
        if is_add:
            # 新增收藏
            param["d"]["action"] = "add"
        else:
            # 删除收藏
            param["d"]["action"] = "remove"
        fill_param_sign(param, path, True)
        await request.post_json(url, self.header, param, self.session)

    async def start_sleep(self):
        param = copy.deepcopy(self.param)
        path = "/api/bff/start-welfare-sleep-v1"
        url = f"{self.domain}/proxy{path}"
        fill_param_sign(param, path, False)
        res = await request.post_json(url, self.header, param, self.session)
        if res and json.loads(res)["code"] == 0:
            log.info("轻国接受睡觉任务")
        else:
            if res:
                log.debug(json.loads(res))
            log.info("轻国接受睡觉任务失败")

    async def complete_sign(self):
        param = copy.deepcopy(self.param)
        path = "/api/bff/claim-welfare-sign-v1"
        url = f"{self.domain}/proxy{path}"
        fill_param_sign(param, path, True)
        res = await request.post_json(url, self.header, param, self.session)
        if res and json.loads(res)["code"] == 0:
            log.info("轻国每日签到完成")
            # 刷新
            await self.valid_cookie()
            log.info(f"轻币：{self.user_info['coin']} 经验：{self.user_info['exp']}")
        else:
            if res:
                log.debug(json.loads(res))
            log.info("轻国每日签到失败")

    async def complete_task(self, task_id: int):
        param = copy.deepcopy(self.param)
        path = "/api/bff/claim-welfare-task-v1"
        url = f"{self.domain}/proxy{path}"
        param["d"]["task_id"] = task_id
        fill_param_sign(param, path, True)
        res = await request.post_json(url, self.header, param, self.session)
        if res and json.loads(res)["code"] == 0:
            log.info(f"轻国{json.loads(res)['data']['task']['title']}任务完成")
            # 刷新
            await self.valid_cookie()
            log.info(f"轻币：{self.user_info['coin']} 经验：{self.user_info['exp']}")
        else:
            if res:
                log.debug(json.loads(res))
            log.info(f"轻国完成任务失败，任务id：{task_id}")


# 解包apk的合法请求算法 禁止外传
SIGN_KEY = "ln_stage_read_api_v1_20260408"
NONCE_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"


def gen_nonce(length: int = 12) -> str:
    return "".join(secrets.choice(NONCE_ALPHABET) for _ in range(length))


def normalize_dict(value: Any) -> Any:
    # 递归按字典序排序
    if isinstance(value, dict):
        return {str(k): normalize_dict(value[k]) for k in sorted(value.keys())}
    if isinstance(value, list):
        return [normalize_dict(v) for v in value]
    return value


def gen_sign(path: str, ts: int, nonce: str, d: dict[str, Any]) -> str:
    # HMAC-SHA256
    trimmed = path[1:] if path.startswith("/") else path
    canon = json.dumps(normalize_dict(d), separators=(",", ":"), ensure_ascii=False)
    msg = "\n".join([trimmed, "app", "android", str(ts), nonce, canon])
    return hmac.new(SIGN_KEY.encode(), msg.encode(), hashlib.sha256).hexdigest()


def fill_param_sign(param: dict[str, Any], path: str, fill_inner_nonce: bool):
    # 外层时间戳
    ts = int(time.time())
    param["ts"] = ts
    # 外层nonce
    outer_nonce = gen_nonce(12)
    # 部分接口内层也要填充
    if fill_inner_nonce:
        # 内层nonce
        param["d"]["nonce"] = gen_nonce(16)
        # 内层时间戳
        param["d"]["ts"] = ts
    # sign
    param["sign"] = gen_sign(path, ts, outer_nonce, param["d"])
