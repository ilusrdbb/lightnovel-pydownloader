from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TaskMode(str, Enum):
    SINGLE_LINK = "single_link"
    COLLECTION_PAGE = "collection_page"
    PAGE_RANGE = "page_range"


class LoginMode(str, Enum):
    ACCOUNT_PASSWORD = "account_password"
    COOKIE = "cookie"


class TaskState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


SUPPORTED_SITES = ("esj", "masiro", "lk", "yuri")


@dataclass
class TaskForm:
    site: str = "esj"
    task_mode: TaskMode = TaskMode.SINGLE_LINK
    single_url: str = ""
    start_page: int = 1
    end_page: int = 1
    login_mode: LoginMode = LoginMode.ACCOUNT_PASSWORD
    username: str = ""
    password: str = ""
    cookie: str = ""
    is_purchase: bool = False
    max_purchase: int = 20
    convert_hans: bool = False
    proxy_url: str = ""
    convert_txt: bool = False


@dataclass
class TaskStatus:
    state: TaskState = TaskState.IDLE
    message: str = "空闲"
    site: str = ""
