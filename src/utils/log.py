import logging
import time
from logging.handlers import TimedRotatingFileHandler
from threading import Lock
from typing import Callable, List

from src.utils.config import read_config
from src.utils.paths import get_log_dir


class Logger:
    def __init__(self):
        self.logger = None
        self.current_day = None
        self.formatter = logging.Formatter("%(asctime)s - %(message)s")
        self.listeners: List[Callable[[str], None]] = []
        self.listener_lock = Lock()

    def init_log(self):
        today = time.strftime("%Y-%m-%d")
        # 如果日期未变化且日志器已初始化，直接返回
        if self.logger and today == self.current_day:
            return
        self.current_day = today
        log_path = get_log_dir()
        log_path.mkdir(parents=True, exist_ok=True)
        # 创建按天滚动的FileHandler
        log_file = log_path / f"{today}.log"
        # 每天0点切换 日志保留90天
        file_handler = TimedRotatingFileHandler(
            filename=str(log_file),
            when="midnight",
            interval=1,
            backupCount=90,
            encoding="utf8"
        )
        file_handler.suffix = "%Y-%m-%d.log"
        # 控制台Handler
        console_handler = logging.StreamHandler()
        file_handler.setFormatter(self.formatter)
        console_handler.setFormatter(self.formatter)
        # 初始化Logger
        self.logger = logging.getLogger("DailyLogger")
        self.logger.setLevel(logging.DEBUG)
        # 清除旧Handler避免重复
        if self.logger.handlers:
            for handler in self.logger.handlers[:]:
                self.logger.removeHandler(handler)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def subscribe(self, listener: Callable[[str], None]):
        with self.listener_lock:
            self.listeners.append(listener)

        def unsubscribe():
            with self.listener_lock:
                if listener in self.listeners:
                    self.listeners.remove(listener)

        return unsubscribe

    def _notify_listeners(self, level: int, message: str):
        record = logging.LogRecord("DailyLogger", level, "", 0, message, (), None)
        formatted_message = self.formatter.format(record)
        with self.listener_lock:
            listeners = list(self.listeners)
        for listener in listeners:
            try:
                listener(formatted_message)
            except Exception:
                continue

    def _debug_enabled(self) -> bool:
        try:
            return read_config("log_level") == "DEBUG"
        except Exception:
            return False

    def _log(self, level: int, message: str):
        self.init_log()
        self.logger.log(level, message)
        self._notify_listeners(level, message)

    def info(self, message):
        self._log(logging.INFO, message)

    def debug(self, message):
        # debug日志
        if self._debug_enabled():
            self._log(logging.DEBUG, message)

    def error(self, message):
        self._log(logging.ERROR, message)


# 全局单例日志对象
log = Logger()
