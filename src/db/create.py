from src.db import BaseDB, engine


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(BaseDB.metadata.create_all)
