import aiohttp

from src.db.book import get_book_by_id, get_all_book, get_books_by_ids
from src.db.chapter import get_chapter, get_chapter_list, get_nopay_chapters
from src.db.pic import clear_all_pic, fail_pic_list, update_pic, get_pic_list
from src.epub.epub import build_epub
from src.epub.txt import build_txt
from src.sites.esj import Esj
from src.sites.fish import Fish
from src.sites.lk import LK
from src.sites.masiro import Masiro
from src.sites.yuri import Yuri
from src.utils import request
from src.utils.config import read_config
from src.utils.log import log


class Process(object):

    async def run(self):
        flag = True
        if read_config("clear_pic_table"):
            # 删图片库
            await self.clear_pic_table()
            flag = False
        if read_config("download_pic_again"):
            # 重新下载图片
            await self.download_pic_again()
            flag = False
        if read_config("export_epub_again"):
            # 重新导出epub
            await self.export_epub_again()
            flag = False
        if not flag:
            return
        for site in read_config("sites"):
            jar = aiohttp.CookieJar()
            conn = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=conn, cookie_jar=jar) as session:
                if site == "esj":
                    await Esj(session).run()
                if site == "lk":
                    await LK(session).run()
                if site == "masiro":
                    await Masiro(session).run()
                if site == "yuri":
                    await Yuri(session).run()
                if site == "fish":
                    await Fish(session).run()
        log.info("本次爬取任务结束")

    @staticmethod
    async def clear_pic_table():
        log.info("开始清空全部图片数据...")
        await clear_all_pic()
        log.info("图片数据已清空")

    @staticmethod
    async def download_pic_again():
        pic_list = await fail_pic_list()
        if not pic_list:
            return
        log.info("开始重新下载图片...")
        pic_header = {
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, zstd",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
        }
        jar = aiohttp.CookieJar()
        conn = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=conn, cookie_jar=jar) as session:
            for pic in pic_list:
                # 获取章节
                chapter = await get_chapter(pic.chapter_table_id)
                # 获取书籍
                book = await get_book_by_id(chapter.book_table_id)
                # 下载图片
                save_path = f"{read_config('image_dir')}/{book.source}/{book.book_id}/{chapter.chapter_id}"
                pic_path = await request.download_pic(pic.pic_url, pic_header, save_path, session)
                if pic_path:
                    pic.pic_path = pic_path
                    # 数据库更新图片保存路径
                    await update_pic(pic)
        log.info("重新下载图片结束")

    @staticmethod
    async def export_epub_again():
        books = await get_all_book()
        if not books:
            return
        log.info("开始重新导出epub...")
        for book in books:
            # 查询对应章节
            chapters = await get_chapter_list(book.id)
            if not chapters:
                book.chapters = []
                continue
            book.chapters = chapters
            for chapter in chapters:
                chapter.pics = []
                # 查对应图片
                pics = await get_pic_list(chapter.id)
                if not pics:
                    continue
                chapter.pics = pics
            # epub
            build_epub(book)
            # txt
            if read_config("convert_txt"):
                build_txt(book)
        log.info("重新导出epub结束")
