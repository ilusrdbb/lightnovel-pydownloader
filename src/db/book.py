import uuid
from typing import List

from sqlalchemy import select, update

from src.db import session_scope
from src.models.book import Book
from src.utils.log import log


async def _query_book(book_id: str, source: str, session) -> Book:
    stmt = select(Book).where(Book.source == source).where(Book.book_id == book_id)
    result = await session.execute(stmt)
    return result.scalars().first()

async def get_book(book_id: str, source: str) -> Book:
    async with session_scope() as session:
        book = await _query_book(book_id, source, session)
        log.debug(f"db query {str(book)}")
        return book

async def update_book(data: Book) -> bool:
    async with session_scope() as session:
        book = await _query_book(data.book_id, data.source, session)
        if book:
            data.id = book.id
            # 更新
            if book.book_name != data.book_name:
                stmt = update(Book).where(Book.id == book.id).values(book_name=data.book_name)
                await session.execute(stmt)
                log.debug(f"db update Book book_name {data.book_name}")
            if data.cover_url and book.cover_url != data.cover_url:
                stmt = update(Book).where(Book.id == book.id).values(cover_url=data.cover_url)
                await session.execute(stmt)
                log.debug(f"db update Book cover_url {data.cover_url}")
                return True
        else:
            # 新增
            data.id = str(uuid.uuid4())
            session.add(data)
            log.debug(f"db insert {str(data)}")
            if data.cover_url:
                return True
        return False

async def get_book_by_id(id: str) -> Book:
    async with session_scope() as session:
        stmt = select(Book).where(Book.id == id)
        result = await session.execute(stmt)
        return result.scalars().first()

async def get_all_book() -> List[Book]:
    async with session_scope() as session:
        stmt = select(Book)
        result = await session.execute(stmt)
        return result.scalars().all()

async def get_books_by_ids(ids: List[str]) -> List[Book]:
    async with session_scope() as session:
        stmt = select(Book).where(Book.id.in_(ids))
        result = await session.execute(stmt)
        return result.scalars().all()
