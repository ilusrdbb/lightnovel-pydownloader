# 版本号
VERSION = "3.3.1"

# 站点
SITES = ["esj", "masiro", "lk", "yuri", "fish", "hameln"]

# 配置文件名称
CONFIG_FILE = "config.yaml"
ADVANCE_FILE = "advance.yaml"

# 数据库路径
DATABASE_URL = "sqlite+aiosqlite:///lightnovel.db"

# 日志路径
LOG_DIR = "./log"
# 日志保留天数
LOG_RETENTION_DAYS = 90

# 时区
TIMEZONE = "Asia/Shanghai"
# 定时任务错过宽限期（秒）
MISFIRE_GRACE_TIME = 600
MAX_SCHEDULER_INSTANCES = 1

# 最大线程数上限
MAX_THREAD = 8
# 请求重试次数
RETRY_COUNT = 3

# Windows文件名非法字符替换
CHAR_MAP = {
    "/": " ",
    "<": "《",
    ">": "》",
    ":": "：",
    '"': "“",
    "|": " ",
    "?": "？",
    "*": "⁎",
    "\\": " ",
}
# 书名过长时截断长度
NAME_TRIM_LENGTH = 80
# 触发截断的书名长度阈值
NAME_TRIM_THRESHOLD = 85

# 轻国跳过爬取置顶书籍id
LK_IGNORE_IDS = ["969547", "1113228", "1099310", "1048596"]
# 轻国单本/合集分界值 小于此值为合集大于为单本
LK_SERIES_THRESHOLD = 100000

# GUI日志轮询间隔（毫秒）
GUI_POLL_INTERVAL = 250
