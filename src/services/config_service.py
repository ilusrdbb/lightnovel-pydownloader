from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

from src.services.gui_state_service import GuiStateService
from src.services.keychain_store import KeychainStore
from src.services.models import LoginMode, SUPPORTED_SITES, TaskForm, TaskMode, UpdateStrategy
from src.utils.config import get_config_file_path, load_config_files, normalize_config_data
from src.utils.paths import get_default_output_root, get_log_dir


class ConfigService:
    def __init__(self):
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.width = 4096
        self.gui_state_service = GuiStateService()
        self.credential_store = KeychainStore()

    def load_form(self) -> TaskForm:
        config = normalize_config_data(load_config_files())
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

        login_bundle = self.load_login_bundle(site, config)

        return TaskForm(
            site=site,
            task_name="",
            task_mode=task_mode,
            single_url=single_url,
            start_page=int(config.get("start_page", 1) or 1),
            end_page=int(config.get("end_page", 1) or 1),
            update_strategy=UpdateStrategy(str(config.get("update_strategy", UpdateStrategy.ONLY_NEW.value))),
            login_mode=login_bundle["login_mode"],
            remember_account=login_bundle["remember_account"],
            remember_password=login_bundle["remember_password"],
            username=login_bundle["username"],
            password=login_bundle["password"],
            cookie=login_bundle["cookie"],
            chrome_path=str(config.get("chrome_path", "") or ""),
            output_root=str(config.get("output_root", "") or ""),
            is_purchase=bool(config.get("is_purchase", False)),
            max_purchase=int(config.get("max_purchase", 20) or 20),
            convert_hans=bool(config.get("convert_hans", False)),
            proxy_url=str(config.get("proxy_url", "") or ""),
            convert_txt=bool(config.get("convert_txt", False)),
        )

    def validate_form(self, form: TaskForm) -> List[str]:
        errors: List[str] = []
        update_strategy_value = (
            form.update_strategy.value
            if isinstance(form.update_strategy, UpdateStrategy)
            else str(form.update_strategy)
        )

        if form.site not in SUPPORTED_SITES:
            errors.append("validation.unsupported_site")

        if form.task_mode == TaskMode.SINGLE_LINK and not form.single_url.strip():
            errors.append("validation.single_url_required")

        if form.task_mode != TaskMode.SINGLE_LINK:
            if form.start_page < 1 or form.end_page < 1:
                errors.append("validation.page_number_positive")
            if form.end_page < form.start_page:
                errors.append("validation.end_page_before_start")

        if form.site in ("esj", "masiro"):
            if form.login_mode == LoginMode.COOKIE:
                if not form.cookie.strip():
                    errors.append("validation.cookie_required")
            elif not form.username.strip() or not form.password.strip():
                errors.append("validation.account_password_required")
        elif form.site == "lk":
            if not form.username.strip() or not form.password.strip():
                errors.append("validation.lk_account_password_required")
        elif form.site == "yuri" and not form.cookie.strip():
            errors.append("validation.yuri_cookie_required")

        if form.max_purchase < 0:
            errors.append("validation.max_purchase_negative")

        if update_strategy_value not in {strategy.value for strategy in UpdateStrategy}:
            errors.append("validation.update_strategy_invalid")

        if form.output_root.strip():
            output_root = Path(form.output_root).expanduser()
            if output_root.exists() and not output_root.is_dir():
                errors.append("validation.output_root_not_directory")

        if form.chrome_path.strip():
            chrome_path = Path(form.chrome_path).expanduser()
            if not chrome_path.is_file():
                errors.append("validation.chrome_path_missing")

        return errors

    def save_form(self, form: TaskForm) -> Dict[str, Any]:
        main_doc = self._load_yaml_doc(get_config_file_path("config.yaml"))
        advance_doc = self._load_yaml_doc(get_config_file_path("advance.yaml"))
        current_config = normalize_config_data(load_config_files())
        update_strategy_value = (
            form.update_strategy.value
            if isinstance(form.update_strategy, UpdateStrategy)
            else str(form.update_strategy)
        )

        main_doc["sites"] = [form.site]
        main_doc["start_page"] = max(1, int(form.start_page))
        main_doc["end_page"] = max(main_doc["start_page"], int(form.end_page))
        main_doc["proxy_url"] = form.proxy_url.strip()
        main_doc["is_purchase"] = bool(form.is_purchase)
        main_doc["max_purchase"] = int(form.max_purchase)
        main_doc["convert_hans"] = bool(form.convert_hans)

        selected_output_root = form.output_root.strip() or str(advance_doc.get("output_root", "") or current_config.get("output_root") or get_default_output_root())
        advance_doc["output_root"] = selected_output_root
        advance_doc["epub_dir"] = str(Path(selected_output_root).expanduser() / "epub")
        advance_doc["txt_dir"] = str(Path(selected_output_root).expanduser() / "txt")
        advance_doc["image_dir"] = str(Path(selected_output_root).expanduser() / "images")
        if form.chrome_path.strip():
            advance_doc["chrome_path"] = form.chrome_path.strip()
        elif "chrome_path" not in advance_doc:
            advance_doc["chrome_path"] = ""

        if form.task_mode == TaskMode.SINGLE_LINK:
            main_doc["white_list"] = [form.single_url.strip()]
        else:
            main_doc["white_list"] = []
            advance_doc["get_collection"] = form.task_mode == TaskMode.COLLECTION_PAGE

        advance_doc["convert_txt"] = bool(form.convert_txt)
        advance_doc["update_strategy"] = update_strategy_value

        login_info = main_doc.setdefault("login_info", CommentedMap())
        site_login = login_info.setdefault(form.site, CommentedMap())
        previous_state = self.gui_state_service.get_site_login_state(form.site)
        previous_password_account = str(previous_state.get("password_account") or site_login.get("username") or "")
        previous_plain_password = str(site_login.get("password", "") or "")

        if form.site in ("esj", "masiro"):
            site_login.setdefault("username", "")
            site_login.setdefault("password", "")
            site_login.setdefault("cookie", "")
            if form.login_mode == LoginMode.COOKIE:
                site_login["cookie"] = form.cookie.strip()
                self._save_login_preferences(
                    form.site,
                    remember_account=previous_state.get("remember_account", False),
                    remember_password=previous_state.get("remember_password", False),
                    password_storage=str(previous_state.get("password_storage", "") or ""),
                    password_account=str(previous_state.get("password_account", "") or ""),
                )
            else:
                self._persist_account_credentials(form, site_login, previous_password_account, previous_plain_password)
        elif form.site == "lk":
            site_login.setdefault("username", "")
            site_login.setdefault("password", "")
            self._persist_account_credentials(form, site_login, previous_password_account, previous_plain_password)
        elif form.site == "yuri":
            site_login.setdefault("cookie", "")
            site_login["cookie"] = form.cookie.strip()

        self._dump_yaml_doc(get_config_file_path("config.yaml"), main_doc)
        self._dump_yaml_doc(get_config_file_path("advance.yaml"), advance_doc)

        runtime_config = load_config_files()
        scheduler_config = deepcopy(runtime_config.get("scheduler_config", {}))
        scheduler_config["enabled"] = False
        runtime_config["scheduler_config"] = scheduler_config
        normalized_runtime = normalize_config_data(runtime_config)
        self._apply_form_credentials_to_runtime(normalized_runtime, form)
        return normalized_runtime

    def get_output_dir(self) -> str:
        config = normalize_config_data(load_config_files())
        return str(Path(config["output_root"]))

    def get_log_dir(self) -> str:
        return str(get_log_dir())

    def is_password_storage_available(self) -> bool:
        return self.credential_store.is_available()

    def load_login_bundle(self, site: str, config: Dict[str, Any] | None = None) -> Dict[str, Any]:
        config = config or normalize_config_data(load_config_files())
        login_info = (config.get("login_info") or {}).get(site, {})
        gui_state = self.gui_state_service.get_site_login_state(site)
        login_mode = self._infer_login_mode(site, login_info, gui_state)
        stored_username = str(login_info.get("username", "") or "")
        stored_password = str(login_info.get("password", "") or "")
        remember_account = bool(gui_state.get("remember_account") or stored_username)
        remember_password = bool(gui_state.get("remember_password") or stored_password)
        keychain_account = str(gui_state.get("password_account") or stored_username or "").strip()
        if remember_password and not stored_password and keychain_account:
            stored_password = self.credential_store.load_password(site, keychain_account) or ""
        return {
            "login_mode": login_mode,
            "remember_account": remember_account,
            "remember_password": remember_password,
            "username": stored_username if remember_account else "",
            "password": stored_password if remember_password else "",
            "cookie": str(login_info.get("cookie", "") or ""),
        }

    def _infer_login_mode(
        self,
        site: str,
        login_info: Dict[str, Any],
        gui_state: Dict[str, Any] | None = None,
    ) -> LoginMode:
        gui_state = gui_state or {}
        if site in ("esj", "masiro"):
            if login_info.get("username") and (
                login_info.get("password")
                or gui_state.get("remember_password")
                or gui_state.get("remember_account")
            ):
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

    def _persist_account_credentials(
        self,
        form: TaskForm,
        site_login: CommentedMap,
        previous_password_account: str,
        previous_plain_password: str,
    ):
        remember_account = bool(form.remember_account)
        remember_password = bool(form.remember_password and remember_account)
        username = form.username.strip()
        site_login["username"] = username if remember_account else ""
        if remember_password and self.credential_store.is_available() and username:
            if previous_password_account and previous_password_account != username:
                self.credential_store.delete_password(form.site, previous_password_account)
            if form.password:
                self.credential_store.save_password(form.site, username, form.password)
                site_login["password"] = ""
                self._save_login_preferences(form.site, True, True, "keychain", username)
                return
            if self.credential_store.load_password(form.site, username):
                site_login["password"] = ""
                self._save_login_preferences(form.site, True, True, "keychain", username)
                return

        if previous_password_account and (not remember_password or previous_password_account != username):
            self.credential_store.delete_password(form.site, previous_password_account)

        if remember_password and previous_plain_password and not self.credential_store.is_available():
            site_login["password"] = previous_plain_password
            self._save_login_preferences(form.site, remember_account, True, "legacy_yaml", username or previous_password_account)
            return

        site_login["password"] = ""
        self._save_login_preferences(form.site, remember_account, False, "", "")

    def _save_login_preferences(
        self,
        site: str,
        remember_account: bool,
        remember_password: bool,
        password_storage: str,
        password_account: str,
    ):
        self.gui_state_service.save_site_login_state(
            site=site,
            remember_account=remember_account,
            remember_password=remember_password,
            password_storage=password_storage,
            password_account=password_account,
        )

    def _apply_form_credentials_to_runtime(self, runtime_config: Dict[str, Any], form: TaskForm):
        login_info = runtime_config.setdefault("login_info", {})
        site_login = login_info.setdefault(form.site, {})
        if form.site in ("esj", "masiro"):
            site_login.setdefault("username", "")
            site_login.setdefault("password", "")
            site_login.setdefault("cookie", "")
            if form.login_mode == LoginMode.COOKIE:
                site_login["cookie"] = form.cookie.strip()
                site_login["username"] = ""
                site_login["password"] = ""
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
