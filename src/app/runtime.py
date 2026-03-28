import asyncio
import signal
from copy import deepcopy
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.core.process import Process
from src.db import engine
from src.db.create import init_db
from src.utils.config import load_config, read_config
from src.utils.log import log

VERSION = "3.1.0"


async def _task_runner():
    await Process().run()


async def _close_engine():
    await engine.dispose()


async def run_async(enable_scheduler: bool = True) -> bool:
    await init_db()
    loop = asyncio.get_running_loop()
    shutdown_event = asyncio.Event()

    def handle_sigterm():
        log.info("接收到终止信号，准备退出...")
        shutdown_event.set()

    try:
        loop.add_signal_handler(signal.SIGTERM, handle_sigterm)
        loop.add_signal_handler(signal.SIGINT, handle_sigterm)
    except (NotImplementedError, RuntimeError):
        # Windows 和部分 GUI 线程不支持直接注册信号处理
        pass

    scheduler_config = read_config("scheduler_config")
    scheduler_enabled = enable_scheduler and scheduler_config["enabled"]
    success = True

    try:
        if scheduler_enabled:
            scheduler = AsyncIOScheduler(
                event_loop=loop,
                timezone=ZoneInfo("Asia/Shanghai")
            )
            scheduler.add_job(
                _task_runner,
                "cron",
                hour=scheduler_config["hour"],
                minute=scheduler_config["minute"],
                misfire_grace_time=600,
                coalesce=False,
                max_instances=1
            )
            log.info("已注册定时任务")
            scheduler.start()
            try:
                await shutdown_event.wait()
            except asyncio.CancelledError:
                pass
            finally:
                log.info("正在停止定时任务...")
                scheduler.shutdown()
        else:
            await _task_runner()
    except Exception as exc:
        success = False
        log.error(f"运行出错: {exc}")
    finally:
        await _close_engine()
        log.info("程序已退出")

    return success


def run_sync(config_data: Optional[Dict[str, Any]] = None, enable_scheduler: bool = True) -> bool:
    runtime_config = deepcopy(config_data) if config_data is not None else None
    load_config(runtime_config)
    log.init_log()
    log.info(f"lightnovel-pydownloader version {VERSION}")
    try:
        return asyncio.run(run_async(enable_scheduler=enable_scheduler))
    except KeyboardInterrupt:
        return True
    except Exception as exc:
        log.error(f"运行失败: {exc}")
        return False
