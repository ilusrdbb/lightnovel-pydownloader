import aiohttp

from sites.lk import Lk
from sites.masiro import Masiro
from sqlite.database import Database
from utils import config, epub, image, log


class Reload(object):

    def __init__(self):
        pass

    async def re_pay(self):
        # 全部打钱失败的章节
        with Database() as db:
            nopay_list = db.chapter.get_nopay_list()
        if not nopay_list:
            return
        book_ids = set()
        for nopay_chapter in nopay_list:
            if nopay_chapter.id == '56dcf8f8-7678-4b23-bed7-b165d080bee5':
                book_ids.add(nopay_chapter.book_table_id)
        # 获取全部需要再次爬的书
        with Database() as db:
            books = db.book.get_by_ids(list(book_ids))
        if not books:
            return
        jar = aiohttp.CookieJar(unsafe=True)
        conn = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=conn, trust_env=True, cookie_jar=jar) as session:
            for book in books:
                if book.source == "lk":
                    lk = Lk(session)
                    await lk.login()
                    # 获取书籍下全部章节
                    with Database() as db:
                        chapters = db.chapter.get_by_book(book.id)
                    for chapter in chapters:
                        if not lk.update_chapter(chapter, chapters):
                            await lk.build_content(book, chapter)
                    epub.build_epub(book, chapters)
                if book.source == "masiro":
                    masiro = Masiro(session)
                    await masiro.login()
                    book_url = config.read("url_config")[self.site]["book"] % book.book_id
                    await masiro.build_book(book_url)

    async def re_download(self):
        book_dict = {}
        chapter_dict = {}
        # 全部未下载的图片
        with Database() as db:
            fail_list = db.pic.get_null_list()
        if not fail_list:
            return
        jar = aiohttp.CookieJar(unsafe=True)
        conn = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=conn, trust_env=True, cookie_jar=jar) as session:
            for pic in fail_list:
                chapter = chapter_dict.get(pic.chapter_table_id)
                if not chapter:
                    with Database() as db:
                        chapter = db.chapter.get_one(pic.chapter_table_id)
                        chapter_dict[chapter.id] = chapter
                book = book_dict.get(chapter.book_table_id)
                if not book:
                    with Database() as db:
                        book = db.book.get_by_id(chapter.book_table_id)
                        book_dict[book.id] = book
                # 重新下载
                log.info("%s 重新下载..." % pic.pic_url)
                await image.download(pic, book.source, book.book_id, chapter.chapter_id, session)
                if pic.pic_path:
                    with Database() as db:
                        db.pic.insert_or_update(pic)
                    log.info("%s 下载成功" % pic.pic_url)
                else:
                    log.info("%s 下载失败" % pic.pic_url)
        # 重新构建涉及到的书籍和章节
        for book in book_dict.values():
            with Database() as db:
                chapters = db.chapter.get_by_book(book.id)
            epub.build_epub(book, chapters)
