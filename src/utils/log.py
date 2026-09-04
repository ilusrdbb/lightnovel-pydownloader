import logging
import os
import time
import sys
import io
from logging.handlers import TimedRotatingFileHandler

from src.core.constants import LOG_DIR, LOG_RETENTION_DAYS
from src.utils.config import read_config

# 将Buffer包装为UTF-8
if hasattr(sys.stdout, 'buffer') and getattr(sys.stdout, 'encoding', '').lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
if hasattr(sys.stderr, 'buffer') and getattr(sys.stderr, 'encoding', '').lower() != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)

# 日志过滤器
class LogFilter(logging.Filter):
    def filter(self, record):
        return "Error while closing connector" not in record.getMessage()

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
        log_path = LOG_DIR
        if not os.path.exists(log_path):
            os.makedirs(log_path)
        # 按天滚动的 FileHandler
        log_file = os.path.join(log_path, f'{today}.log')
        file_handler = TimedRotatingFileHandler(
            filename=log_file,
            when="midnight",
            interval=1,
            backupCount=LOG_RETENTION_DAYS,
            encoding="utf8"
        )
        file_handler.suffix = "%Y-%m-%d.log"
        # 控制台Handler
        console_handler = logging.StreamHandler(sys.stdout)
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
        # 屏蔽aiohttp关闭连接池时因服务端断开keep-alive连接的脏日志
        root_logger = logging.getLogger()
        if not any(isinstance(f, LogFilter) for f in root_logger.filters):
            root_logger.addFilter(LogFilter())

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
