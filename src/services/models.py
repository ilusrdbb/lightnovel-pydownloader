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


class UpdateStrategy(str, Enum):
    ONLY_NEW = "only_new"
    REFRESH_CHANGED = "refresh_changed"
    FULL_REFETCH = "full_refetch"


class TaskState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


SUPPORTED_SITES = ("esj", "masiro", "lk", "yuri")


@dataclass
class TaskForm:
    site: str = "esj"
    task_name: str = ""
    task_mode: TaskMode = TaskMode.SINGLE_LINK
    single_url: str = ""
    start_page: int = 1
    end_page: int = 1
    update_strategy: UpdateStrategy = UpdateStrategy.ONLY_NEW
    login_mode: LoginMode = LoginMode.ACCOUNT_PASSWORD
    remember_account: bool = False
    remember_password: bool = False
    username: str = ""
    password: str = ""
    cookie: str = ""
    chrome_path: str = ""
    output_root: str = ""
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
