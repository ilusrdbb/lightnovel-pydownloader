from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Tuple

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

from src.services.models import LoginMode, SUPPORTED_SITES, TaskForm, TaskMode
from src.utils.config import get_config_file_path, load_config_files, normalize_config_data
from src.utils.paths import get_log_dir


class ConfigService:
    def __init__(self):
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.width = 4096

    def load_form(self) -> TaskForm:
        config = load_config_files()
        sites = config.get("sites") or ["esj"]
        site = sites[0] if sites[0] in SUPPORTED_SITES else "esj"
        white_list = config.get("white_list") or []

        task_mode = TaskMode.SINGLE_LINK
        single_url = ""
        if white_list:
            task_mode = TaskMode.SINGLE_LINK
            single_url = str(white_list[0])
        elif config.get("get_collection", True):
            task_mode = TaskMode.COLLECTION_PAGE
        else:
            task_mode = TaskMode.PAGE_RANGE

        login_info = (config.get("login_info") or {}).get(site, {})
        login_mode = self._infer_login_mode(site, login_info)

        return TaskForm(
            site=site,
            task_mode=task_mode,
            single_url=single_url,
            start_page=int(config.get("start_page", 1) or 1),
            end_page=int(config.get("end_page", 1) or 1),
            login_mode=login_mode,
            username=str(login_info.get("username", "") or ""),
            password=str(login_info.get("password", "") or ""),
            cookie=str(login_info.get("cookie", "") or ""),
            is_purchase=bool(config.get("is_purchase", False)),
            max_purchase=int(config.get("max_purchase", 20) or 20),
            convert_hans=bool(config.get("convert_hans", False)),
            proxy_url=str(config.get("proxy_url", "") or ""),
            convert_txt=bool(config.get("convert_txt", False)),
        )

    def validate_form(self, form: TaskForm) -> List[str]:
        errors: List[str] = []

        if form.site not in SUPPORTED_SITES:
            errors.append("不支持的站点。")

        if form.task_mode == TaskMode.SINGLE_LINK and not form.single_url.strip():
            errors.append("单本链接模式需要填写小说链接。")

        if form.task_mode != TaskMode.SINGLE_LINK:
            if form.start_page < 1 or form.end_page < 1:
                errors.append("页码必须大于 0。")
            if form.end_page < form.start_page:
                errors.append("结束页不能小于开始页。")

        if form.site in ("esj", "masiro"):
            if form.login_mode == LoginMode.COOKIE:
                if not form.cookie.strip():
                    errors.append("当前登录方式需要填写 Cookie。")
            elif not form.username.strip() or not form.password.strip():
                errors.append("当前登录方式需要填写账号和密码。")
        elif form.site == "lk":
            if not form.username.strip() or not form.password.strip():
                errors.append("轻国需要填写账号和密码。")
        elif form.site == "yuri" and not form.cookie.strip():
            errors.append("百合会需要填写 Cookie。")

        if form.max_purchase < 0:
            errors.append("购买上限不能小于 0。")

        return errors

    def save_form(self, form: TaskForm) -> Dict[str, Any]:
        main_doc = self._load_yaml_doc(get_config_file_path("config.yaml"))
        advance_doc = self._load_yaml_doc(get_config_file_path("advance.yaml"))

        main_doc["sites"] = [form.site]
        main_doc["start_page"] = max(1, int(form.start_page))
        main_doc["end_page"] = max(main_doc["start_page"], int(form.end_page))
        main_doc["proxy_url"] = form.proxy_url.strip()
        main_doc["is_purchase"] = bool(form.is_purchase)
        main_doc["max_purchase"] = int(form.max_purchase)
        main_doc["convert_hans"] = bool(form.convert_hans)

        if form.task_mode == TaskMode.SINGLE_LINK:
            main_doc["white_list"] = [form.single_url.strip()]
        else:
            main_doc["white_list"] = []
            advance_doc["get_collection"] = form.task_mode == TaskMode.COLLECTION_PAGE

        advance_doc["convert_txt"] = bool(form.convert_txt)

        login_info = main_doc.setdefault("login_info", CommentedMap())
        site_login = login_info.setdefault(form.site, CommentedMap())

        if form.site in ("esj", "masiro"):
            site_login.setdefault("username", "")
            site_login.setdefault("password", "")
            site_login.setdefault("cookie", "")
            if form.login_mode == LoginMode.COOKIE:
                site_login["username"] = ""
                site_login["password"] = ""
                site_login["cookie"] = form.cookie.strip()
            else:
                site_login["username"] = form.username.strip()
                site_login["password"] = form.password
        elif form.site == "lk":
            site_login.setdefault("username", "")
            site_login.setdefault("password", "")
            site_login["username"] = form.username.strip()
            site_login["password"] = form.password
        elif form.site == "yuri":
            site_login.setdefault("cookie", "")
            site_login["cookie"] = form.cookie.strip()

        self._dump_yaml_doc(get_config_file_path("config.yaml"), main_doc)
        self._dump_yaml_doc(get_config_file_path("advance.yaml"), advance_doc)

        runtime_config = load_config_files()
        scheduler_config = deepcopy(runtime_config.get("scheduler_config", {}))
        scheduler_config["enabled"] = False
        runtime_config["scheduler_config"] = scheduler_config
        return normalize_config_data(runtime_config)

    def get_output_dir(self) -> str:
        config = normalize_config_data(load_config_files())
        return str(Path(config["epub_dir"]))

    def get_log_dir(self) -> str:
        return str(get_log_dir())

    def _infer_login_mode(self, site: str, login_info: Dict[str, Any]) -> LoginMode:
        if site in ("esj", "masiro"):
            if login_info.get("username") and login_info.get("password"):
                return LoginMode.ACCOUNT_PASSWORD
            return LoginMode.COOKIE
        if site == "yuri":
            return LoginMode.COOKIE
        return LoginMode.ACCOUNT_PASSWORD

    def _load_yaml_doc(self, path: str):
        with open(path, "r", encoding="utf-8") as f:
            doc = self.yaml.load(f)  # type: ignore[assignment]
        return doc if doc is not None else CommentedMap()

    def _dump_yaml_doc(self, path: str, doc):
        with open(path, "w", encoding="utf-8") as f:
            self.yaml.dump(doc, f)
