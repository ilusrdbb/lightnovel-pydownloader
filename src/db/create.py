from sqlalchemy import text

from src.db import BaseDB, engine


async def init_db():
    async with engine.connect() as conn:
        # 非事务的执行WAL
        await conn.execute(text("PRAGMA journal_mode=WAL;"))
    async with engine.begin() as conn:
        # 建表
        await conn.run_sync(BaseDB.metadata.create_all)
