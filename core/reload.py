import aiohttp

from sites.esj import Esj
from sites.lk import Lk
from sites.masiro import Masiro
from sqlite.database import Database
from utils import config, epub, push


class Reload(object):

    def __init__(self):
        pass

    async def re_pay(self):
        # 全部打钱失败的章节
        with Database() as db:
            nopay_list = db.chapter.get_nopay_list()
        if nopay_list:
            book_ids = set()
            for nopay_chapter in nopay_list:
                book_ids.add(nopay_chapter.book_table_id)
            # 获取全部需要再次爬的书
            with Database() as db:
                books = db.book.get_by_ids(list(book_ids))
            if books:
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
                            push.calibre(book)
                        if book.source == "masiro":
                            masiro = Masiro(session)
                            await masiro.login()
                            book_url = config.read("url_config")[self.site]["book"] % book.book_id
                            await masiro.build_book(book_url)