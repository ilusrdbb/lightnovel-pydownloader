import uuid

from sqlalchemy import select, delete, update

from src.db import session_scope
from src.models.cookie import Cookie
from src.utils.log import log


async def _delete_by_source(source: str, session):
    stmt = delete(Cookie).where(Cookie.source == source)
    await session.execute(stmt)

async def get_cookie(source: str) -> Cookie:
    async with session_scope() as session:
        stmt = select(Cookie).where(Cookie.source == source)
        result = await session.execute(stmt)
        cookie = result.scalars().first()
        log.debug(f"db query {str(cookie)}")
        return cookie

async def delete_cookie(source: str):
    async with session_scope() as session:
        await _delete_by_source(source, session)
        log.debug(f"db delete Cookie {source}")

async def update_cookie(cookie: Cookie):
    async with session_scope() as session:
        # 先删
        await _delete_by_source(cookie.source, session)
        # 后增
        cookie.id = str(uuid.uuid4())
        session.add(cookie)
        log.debug(f"db insert {str(cookie)}")

async def update_token(source: str, token: str):
    async with session_scope() as session:
        stmt = update(Cookie).where(Cookie.source == source).values(token=token)
        await session.execute(stmt)
