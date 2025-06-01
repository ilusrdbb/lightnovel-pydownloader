import logging
import os
import time
from logging.handlers import TimedRotatingFileHandler

from src.utils.config import read_config


class Logger:
    def __init__(self):
        self.logger = None
        self.current_day = None

    def init_log(self):
        today = time.strftime("%Y-%m-%d")
        # 如果日期未变化且日志器已初始化，直接返回
        if self.logger and today == self.current_day:
            return
        self.current_day = today
        log_path = "./log"
        if not os.path.exists(log_path):
            os.makedirs(log_path)
        # 创建按天滚动的FileHandler
        log_file = os.path.join(log_path, f'{today}.log')
        # 每天0点切换 日志保留90天
        file_handler = TimedRotatingFileHandler(
            filename=log_file,
            when="midnight",
            interval=1,
            backupCount=90,
            encoding="utf8"
        )
        file_handler.suffix = "%Y-%m-%d.log"
        # 控制台Handler
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s - %(message)s")
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        # 初始化Logger
        self.logger = logging.getLogger("DailyLogger")
        self.logger.setLevel(logging.INFO)
        # 清除旧Handler避免重复
        if self.logger.handlers:
            for handler in self.logger.handlers[:]:
                self.logger.removeHandler(handler)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def info(self, message):
        # 每次记录前检查日期
        self.init_log()
        self.logger.info(message)

    def debug(self, message):
        # debug日志
        if read_config("log_level") == "DEBUG":
            self.init_log()
            self.logger.info(message)


# 全局单例日志对象
log = Logger()
