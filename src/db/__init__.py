import traceback
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.ext.declarative import declarative_base

from src.utils.log import log

# 创建异步数据库引擎
engine = create_async_engine("sqlite+aiosqlite:///lightnovel.db")
# 创建异步会话工厂
AsyncSessionFactory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
# 创建基类
BaseDB = declarative_base()
# 提供一个上下文管理器，确保会话正确关闭
@asynccontextmanager
async def session_scope():
    session = AsyncSessionFactory()
    try:
        yield session
        await session.commit()
    except Exception as e:
        log.info(str(e))
        log.debug(traceback.print_exc())
        await session.rollback()
        raise
    finally:
        await session.close()
