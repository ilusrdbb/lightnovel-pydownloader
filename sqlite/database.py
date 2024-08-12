from sqlmodel import Session

from .book import BookDatabase
from .chapter import ChapterDatabase
from .cookie import CookieDatabase
from .engine import engine
from .pic import PicDatabase


class Database(Session):

    def __init__(self, _engine=engine):
        self.engine = _engine
        super().__init__(_engine)
        self.book = BookDatabase(self)
        self.chapter = ChapterDatabase(self)
        self.pic = PicDatabase(self)
        self.cookie = CookieDatabase(self)
