from typing import Optional

from aiohttp import ClientSession
from sqlmodel import Session, select
from utils import common, image

from models.book import Book


class BookDatabase:

    def __init__(self, session: Session):
        self.session = session

    def update(self, data: Book):
        self.session.add(data)
        self.session.commit()
        self.session.refresh(data)

    def get_one(self, book_id: str, source: str) -> Optional[Book]:
        statement = select(Book).where(Book.book_id == book_id, Book.source == source)
        return self.session.exec(statement).first()

    def get_all(self) -> list[Book]:
        statement = select(Book)
        return self.session.exec(statement).all()

    async def insert_or_update(self, data: Book, session: ClientSession):
        book = self.get_one(data.book_id, data.source)
        if not book:
            # 生成封面
            if data.cover_url:
                await image.cover(data.cover_url, data.source, data.book_id, session)
            self.update(data)
            return
        if data.book_name != book.book_name or data.cover_url != book.cover_url:
            book.book_name = data.book_name
            self.update(book)
        if data.cover_url != book.cover_url:
            book.cover_url = data.cover_url
            # 更新封面
            if data.cover_url:
                await image.cover(data.cover_url, data.source, data.book_id, session)
            self.update(book)
        common.copy(book, data)

    def get_by_ids(self, ids: list) -> list[Book]:
        statement = select(Book).where(Book.id.in_(ids))
        return self.session.exec(statement).all()

    def get_by_id(self, id: str) -> Optional[Book]:
        statement = select(Book).where(Book.id == id)
        return self.session.exec(statement).first()
