import asyncio
from zoneinfo import ZoneInfo

from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.core.process import Process
from src.db import engine
from src.db.create import init_db
from src.utils.config import load_config, read_config
from src.utils.log import log

async def task_runner():
    await Process().run()

async def main_async():
    # 初始化数据库
    await init_db()
    # 获取当前事件循环
    current_loop = asyncio.get_running_loop()
    scheduler = AsyncIOScheduler(
        event_loop=current_loop,
        timezone=ZoneInfo("Asia/Shanghai"),
        executors={
            'asyncio': AsyncIOExecutor()
        }
    )
    scheduler_config = read_config("scheduler_config")
    if scheduler_config["enabled"]:
        scheduler.add_job(
            task_runner,
            "cron",
            hour=scheduler_config["hour"],
            minute=scheduler_config["minute"],
            misfire_grace_time=600,
            coalesce=False,
            max_instances=1,
            executor='asyncio'
        )
        log.info("已注册定时任务")
        scheduler.start()
        # 保持主协程运行，直到被中断
        try:
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            log.info("定时任务已停止")
        finally:
            if scheduler.running:
                scheduler.shutdown()
    else:
        # 直接运行
        await task_runner()

async def close_engine():
    await engine.dispose()

if __name__ == '__main__':
    # 初始化配置
    load_config()
    # 初始化日志
    log.init_log()
    log.info(f"lightnovel-pydownloader version 3.0.9")
    try:
        asyncio.run(main_async())
    except Exception as e:
        log.info(str(e))
    finally:
        # 关闭数据库WAL
        asyncio.run(close_engine())
        input("Press Enter to exit...")

