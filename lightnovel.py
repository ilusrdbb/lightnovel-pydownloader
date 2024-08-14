import asyncio
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BlockingScheduler

from core.process import Process
from sqlite import script
from utils import config, log

config.init_config()
scheduler = BlockingScheduler(timezone=ZoneInfo("Asia/Shanghai"))
loop = asyncio.get_event_loop()


def run():
    if config.read("scheduler_config")["enabled"]:
        print("===========start scheduler===========")
    log.init_log()
    script.init_db()
    loop.run_until_complete(Process(config.read("site")).run())
    log.remove_log()
    if config.read("scheduler_config")["enabled"]:
        print("===========end scheduler===========")


if __name__ == '__main__':
    print("Version 2.0.0")
    if config.read("scheduler_config")["enabled"]:
        # 添加定时任务
        scheduler.add_job(
            run,
            "cron",
            hour=config.read("scheduler_config")["hour"],
            minute=config.read("scheduler_config")["minute"],
            misfire_grace_time=600,
            coalesce=True,
            max_instances=1
        )
        scheduler.start()
    else:
        run()
        input("Press Enter to exit...")
