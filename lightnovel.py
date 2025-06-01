import asyncio
from zoneinfo import ZoneInfo

from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.core.process import Process
from src.db.create import init_db
from src.utils.config import load_config, read_config
from src.utils.log import log

scheduler = AsyncIOScheduler(
    timezone=ZoneInfo("Asia/Shanghai"),
    executors={
        'asyncio': AsyncIOExecutor()
    }
)


async def run():
    await Process().run()

if __name__ == '__main__':
    # 初始化数据库
    asyncio.run(init_db())
    # 初始化配置
    load_config()
    # 初始化日志
    log.init_log()
    log.info(f"lightnovel-pydownloader version {read_config('version')}")
    # 显式创建并设置事件循环
    loop = asyncio.new_event_loop()
    scheduler_config = read_config("scheduler_config")
    if scheduler_config["enabled"]:
        # 添加定时任务
        scheduler.add_job(
            run,
            "cron",
            hour=scheduler_config["hour"],
            minute=scheduler_config["minute"],
            misfire_grace_time=600,
            coalesce=False,
            max_instances=1,
            executor='asyncio'
        )
    else:
        # 非定时使用统一的事件循环执行任务
        loop.run_until_complete(run())
    try:
        scheduler.start()
        # 使用显式创建的循环
        loop.run_forever()
    except Exception as e:
        log.info(str(e))
    finally:
        scheduler.shutdown()

