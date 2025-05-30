import uuid

from sqlalchemy import select, update

from src.db import session_scope
from src.models.pic import Pic
from src.utils.log import log


async def get_pic_list(chapter_table_id: str) -> Pic:
    async with session_scope() as session:
        stmt = select(Pic).where(Pic.chapter_table_id == chapter_table_id)
        result = await session.execute(stmt)
        pic = result.scalars().all()
        return pic

async def update_pic(pic: Pic):
    async with session_scope() as session:
        # 更新路径
        stmt = update(Pic).where(Pic.id == pic.id).values(pic_path=pic.pic_path)
        await session.execute(stmt)
        log.debug(f"db update Pic pic_path {pic.pic_path}")

async def insert_pic(pic: Pic):
    async with session_scope() as session:
        # 新增
        pic.id = str(uuid.uuid4())
        session.add(pic)
        log.debug(f"db insert {str(pic)}")