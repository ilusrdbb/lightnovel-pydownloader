import uuid

from sqlalchemy import select, delete

from src.db import session_scope
from src.models.cookie import Cookie
from src.utils.log import log


async def get_cookie(source: str) -> Cookie:
    async with session_scope() as session:
        stmt = select(Cookie).where(Cookie.source == source)
        result = await session.execute(stmt)
        cookie = result.scalars().first()
        log.debug(f"db query {str(cookie)}")
        return cookie

async def delete_cookie(source: str):
    async with session_scope() as session:
        stmt = delete(Cookie).where(Cookie.source == source)
        await session.execute(stmt)
        log.debug(f"db delete Cookie {source}")

async def update_cookie(cookie: Cookie):
    # 先删
    await delete_cookie(cookie.source)
    # 后增
    async with session_scope() as session:
        cookie.id = str(uuid.uuid4())
        session.add(cookie)
        log.debug(f"db insert {str(cookie)}")
