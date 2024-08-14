import asyncio

from apscheduler.schedulers.background import BackgroundScheduler

from core.process import Process
from sqlite import script
from utils import config, log

config.init_config()
scheduler = BackgroundScheduler(timezone='Asia/Shanghai')
loop = asyncio.get_event_loop()


def run():
    print("Version 2.0.0")
    log.init_log()
    script.init_db()
    loop.run_until_complete(Process(config.read("site")).run())
    log.remove_log()


if __name__ == '__main__':
    if config.read("scheduler_config")["enabled"]:
        print("===========start scheduler===========")
        # 添加定时任务
        scheduler.add_job(
            run,
            "cron",
            hour=config.read("scheduler_config")["hour"],
            minute=config.read("scheduler_config")["minute"]
        )
        scheduler.start()
        print("===========end scheduler===========")
    else:
        run()
        input("Press Enter to exit...")
