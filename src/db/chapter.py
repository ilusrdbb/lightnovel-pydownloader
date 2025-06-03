import uuid
from typing import List

from sqlalchemy import select, update

from src.db import session_scope
from src.models.chapter import Chapter
from src.utils.log import log


async def get_chapter_list(book_table_id: str) -> List[Chapter]:
    async with session_scope() as session:
        stmt = select(Chapter).where(Chapter.book_table_id == book_table_id)
        result = await session.execute(stmt)
        return result.scalars().all()

async def update_chapter(chapter: Chapter):
    async with session_scope() as session:
        if chapter.id:
            # 更新
            stmt = update(Chapter).where(Chapter.id == chapter.id).values(
                chapter_name=chapter.chapter_name,
                chapter_order=chapter.chapter_order,
                content=chapter.content,
                last_update_time=chapter.last_update_time,
                purchase_fail_flag=chapter.purchase_fail_flag,
            )
            await session.execute(stmt)
            log.debug(f"db update {str(chapter)}")
        else:
            # 新增
            chapter.id = str(uuid.uuid4())
            session.add(chapter)
            log.debug(f"db insert {str(chapter)}")

async def get_chapter(id: str) -> Chapter:
    async with session_scope() as session:
        stmt = select(Chapter).where(Chapter.id == id)
        result = await session.execute(stmt)
        return result.scalars().first()

async def get_nopay_chapters() -> List[Chapter]:
    async with session_scope() as session:
        stmt = select(Chapter).where(Chapter.purchase_fail_flag == 1)
        result = await session.execute(stmt)
        return result.scalars().all()
