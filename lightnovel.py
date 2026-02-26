import asyncio
import signal
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.core.process import Process
from src.db import engine
from src.db.create import init_db
from src.utils.config import load_config, read_config
from src.utils.log import log

VERSION = "3.1.0"

# 退出标记
shutdown_event = asyncio.Event()

def handle_sigterm():
    log.info("Linux接收到终止信号，准备退出...")
    shutdown_event.set()

async def task_runner():
    await Process().run()

async def main_async():
    # 初始化数据库
    await init_db()
    loop = asyncio.get_running_loop()
    try:
        # Linux注册信号处理
        loop.add_signal_handler(signal.SIGTERM, handle_sigterm)
        loop.add_signal_handler(signal.SIGINT, handle_sigterm)
    except NotImplementedError:
        # Windows不支持直接pass
        pass
    scheduler_config = read_config("scheduler_config")
    try:
        if scheduler_config["enabled"]:
            scheduler = AsyncIOScheduler(
                event_loop=loop,
                timezone=ZoneInfo("Asia/Shanghai")
            )
            scheduler.add_job(
                task_runner,
                "cron",
                hour=scheduler_config["hour"],
                minute=scheduler_config["minute"],
                misfire_grace_time=600,
                coalesce=False,
                max_instances=1
            )
            log.info("已注册定时任务")
            scheduler.start()
            # 保持主协程运行
            try:
                await shutdown_event.wait()
            except asyncio.CancelledError:
                pass
            finally:
                log.info("正在停止定时任务...")
                scheduler.shutdown()
        else:
            await task_runner()
    except Exception as e:
        log.error(f"运行出错: {e}")
    finally:
        await close_engine()
        log.info("程序已退出")

async def close_engine():
    # 关闭数据库WAL
    await engine.dispose()

if __name__ == '__main__':
    # 初始化配置
    load_config()
    # 初始化日志
    log.init_log()
    log.info(f"lightnovel-pydownloader version {VERSION}")
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        # 手动Ctrl+C兜底
        pass

