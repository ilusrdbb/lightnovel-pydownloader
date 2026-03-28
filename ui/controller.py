from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets

from src.bookshelf import BookshelfService
from src.bookshelf.models import BookshelfBook
from src.services.config_service import ConfigService
from src.services.models import (
    LoginMode,
    TaskForm,
    TaskMode,
    TaskState,
    TaskStatus,
    UpdateStrategy,
)
from src.services.task_service import TaskService
from src.services.text_catalog import get_text_catalog
from ui.book_editor_dialog import BookEditorDialog
from ui.main_window import MainWindow


class MainController(QtCore.QObject):
    log_signal = QtCore.Signal(str)
    state_signal = QtCore.Signal(object)
    finished_signal = QtCore.Signal(bool)

    def __init__(self):
        super().__init__()
        self.config_service = ConfigService()
        self.task_service = TaskService(self.config_service)
        self.bookshelf_service = BookshelfService()
        self.texts = get_text_catalog()
        self.window = MainWindow()
        self._selected_bookshelf_id: Optional[int] = None

        self.log_signal.connect(self.window.log_text.appendPlainText)
        self.state_signal.connect(self._apply_status)
        self.finished_signal.connect(self._task_finished)

        self.window.site_combo.currentTextChanged.connect(self._handle_site_changed)
        self.window.task_mode_combo.currentIndexChanged.connect(self._refresh_task_mode_ui)
        self.window.login_mode_combo.currentIndexChanged.connect(self._refresh_login_ui)
        self.window.purchase_checkbox.toggled.connect(self._refresh_login_ui)
        self.window.remember_account_checkbox.toggled.connect(self._handle_remember_account_toggled)
        self.window.remember_password_checkbox.toggled.connect(self._handle_remember_password_toggled)
        self.window.start_button.clicked.connect(self._start_task)
        self.window.open_output_button.clicked.connect(self._open_output_dir)
        self.window.open_log_button.clicked.connect(self._open_log_dir)
        self.window.output_root_button.clicked.connect(self._choose_output_dir)
        self.window.chrome_path_button.clicked.connect(self._choose_chrome_path)
        self.window.bookshelf_panel.table.itemSelectionChanged.connect(self._sync_bookshelf_detail)
        self.window.bookshelf_panel.table.itemDoubleClicked.connect(lambda _item: self._edit_bookshelf_book())
        self.window.bookshelf_panel.add_button.clicked.connect(self._add_bookshelf_book)
        self.window.bookshelf_panel.edit_button.clicked.connect(self._edit_bookshelf_book)
        self.window.bookshelf_panel.delete_button.clicked.connect(self._delete_bookshelf_book)
        self.window.bookshelf_panel.move_up_button.clicked.connect(self._move_bookshelf_book_up)
        self.window.bookshelf_panel.move_down_button.clicked.connect(self._move_bookshelf_book_down)
        self.window.bookshelf_panel.fill_task_button.clicked.connect(self._fill_task_from_bookshelf)

        self._load_initial_form()
        self._refresh_task_mode_ui()
        self._refresh_login_ui()
        self._refresh_bookshelf()

    def show(self):
        self.window.show()

    def _load_initial_form(self):
        form = self.config_service.load_form()
        self.window.site_combo.setCurrentText(form.site)
        self.window.task_name_edit.setText(form.task_name)
        self._set_task_mode(form.task_mode)
        self._set_update_strategy(form.update_strategy)
        self.window.single_url_edit.setText(form.single_url)
        self.window.start_page_spin.setValue(form.start_page)
        self.window.end_page_spin.setValue(form.end_page)
        self.window.chrome_path_edit.setText(form.chrome_path)
        self.window.output_root_edit.setText(form.output_root)
        self.window.purchase_checkbox.setChecked(form.is_purchase)
        self.window.max_purchase_spin.setValue(form.max_purchase)
        self.window.convert_hans_checkbox.setChecked(form.convert_hans)
        self.window.proxy_edit.setText(form.proxy_url)
        self.window.convert_txt_checkbox.setChecked(form.convert_txt)
        self.window.site_value.setText(form.site)
        self._apply_login_bundle(
            form.site,
            form.login_mode,
            form.username,
            form.password,
            form.cookie,
            form.remember_account,
            form.remember_password,
        )

    def _set_task_mode(self, task_mode: TaskMode):
        index = self.window.task_mode_combo.findData(task_mode.value)
        if index >= 0:
            self.window.task_mode_combo.setCurrentIndex(index)

    def _set_login_mode(self, login_mode: LoginMode):
        index = self.window.login_mode_combo.findData(login_mode.value)
        if index >= 0:
            self.window.login_mode_combo.setCurrentIndex(index)

    def _set_update_strategy(self, update_strategy: UpdateStrategy):
        index = self.window.update_strategy_combo.findData(update_strategy.value)
        if index >= 0:
            self.window.update_strategy_combo.setCurrentIndex(index)

    def _current_task_mode(self) -> TaskMode:
        return TaskMode(self.window.task_mode_combo.currentData())

    def _current_login_mode(self) -> LoginMode:
        return LoginMode(self.window.login_mode_combo.currentData())

    def _current_update_strategy(self) -> UpdateStrategy:
        return UpdateStrategy(self.window.update_strategy_combo.currentData())

    def _current_site(self) -> str:
        return self.window.site_combo.currentText()

    def _refresh_task_mode_ui(self):
        is_single_link = self._current_task_mode() == TaskMode.SINGLE_LINK
        self.window.single_url_edit.setVisible(is_single_link)
        self.window.page_range_widget.setVisible(not is_single_link)
        single_link_label = self.window.task_form_layout.labelForField(self.window.single_url_edit)
        page_range_label = self.window.task_form_layout.labelForField(self.window.page_range_widget)
        if single_link_label:
            single_link_label.setVisible(is_single_link)
        if page_range_label:
            page_range_label.setVisible(not is_single_link)
        self.window.update_strategy_combo.setEnabled(is_single_link)
        self.window.update_strategy_hint_label.setVisible(True)

    def _refresh_login_ui(self):
        site = self._current_site()
        login_mode = self._current_login_mode()
        password_storage_available = self.config_service.is_password_storage_available()

        if site == "lk":
            self.window.login_mode_combo.hide()
            self.window.login_stack.setCurrentWidget(self.window.account_form)
            self.window.login_hint_label.hide()
        elif site == "yuri":
            self.window.login_mode_combo.hide()
            self.window.login_stack.setCurrentWidget(self.window.cookie_form)
            self.window.login_hint_label.hide()
        else:
            self.window.login_mode_combo.show()
            if login_mode == LoginMode.COOKIE:
                self.window.login_stack.setCurrentWidget(self.window.cookie_form)
            else:
                self.window.login_stack.setCurrentWidget(self.window.account_form)
            if site == "masiro":
                if login_mode == LoginMode.COOKIE:
                    self.window.login_hint_label.setText(self.texts.get_text("text.login_hint_masiro_cookie"))
                else:
                    self.window.login_hint_label.setText(self.texts.get_text("text.login_hint_masiro_account"))
                self.window.login_hint_label.show()
            else:
                self.window.login_hint_label.hide()

        purchase_supported = site in ("lk", "masiro")
        self.window.purchase_checkbox.setEnabled(purchase_supported)
        self.window.max_purchase_spin.setEnabled(purchase_supported and self.window.purchase_checkbox.isChecked())
        self.window.purchase_hint_label.setVisible(purchase_supported)
        self.window.chrome_path_edit.setEnabled(site == "masiro")
        self.window.chrome_path_button.setEnabled(site == "masiro")
        self.window.chrome_path_hint_label.setVisible(site == "masiro")
        account_site = site in ("esj", "masiro", "lk")
        account_mode_active = account_site and (site == "lk" or login_mode == LoginMode.ACCOUNT_PASSWORD)
        self.window.remember_account_checkbox.setVisible(account_mode_active)
        self.window.remember_password_checkbox.setVisible(account_mode_active)
        self.window.remember_password_checkbox.setEnabled(account_mode_active and password_storage_available)
        self.window.remember_password_hint_label.setVisible(account_mode_active)
        self.window.keychain_status_label.setVisible(account_mode_active and not password_storage_available)
        self.window.site_value.setText(site)
        self._refresh_bookshelf()

    def _collect_form(self) -> TaskForm:
        site = self._current_site()
        login_mode = self._current_login_mode() if site in ("esj", "masiro") else (
            LoginMode.ACCOUNT_PASSWORD if site == "lk" else LoginMode.COOKIE
        )
        return TaskForm(
            site=site,
            task_name=self.window.task_name_edit.text().strip(),
            task_mode=self._current_task_mode(),
            single_url=self.window.single_url_edit.text().strip(),
            start_page=self.window.start_page_spin.value(),
            end_page=self.window.end_page_spin.value(),
            update_strategy=self._current_update_strategy(),
            login_mode=login_mode,
            remember_account=self.window.remember_account_checkbox.isChecked(),
            remember_password=self.window.remember_password_checkbox.isChecked(),
            username=self.window.username_edit.text().strip(),
            password=self.window.password_edit.text(),
            cookie=self.window.cookie_edit.toPlainText().strip(),
            chrome_path=self.window.chrome_path_edit.text().strip(),
            output_root=self.window.output_root_edit.text().strip(),
            is_purchase=self.window.purchase_checkbox.isChecked(),
            max_purchase=self.window.max_purchase_spin.value(),
            convert_hans=self.window.convert_hans_checkbox.isChecked(),
            proxy_url=self.window.proxy_edit.text().strip(),
            convert_txt=self.window.convert_txt_checkbox.isChecked(),
        )

    def _start_task(self):
        form = self._collect_form()
        self.window.log_text.clear()
        self.window.book_value.setText("-")
        self.window.chapter_value.setText("-")
        self.window.site_value.setText(form.site)
        try:
            self.task_service.start_task(
                form,
                on_log=self.log_signal.emit,
                on_state=self.state_signal.emit,
                on_finished=self.finished_signal.emit,
            )
            self.window.start_button.setEnabled(False)
        except ValueError as exc:
            QtWidgets.QMessageBox.warning(
                self.window,
                self.texts.get_text("dialog.incomplete_info_title"),
                self._friendly_validation_message(str(exc), form),
            )
        except RuntimeError as exc:
            QtWidgets.QMessageBox.information(
                self.window,
                self.texts.get_text("dialog.task_running_title"),
                self.texts.get_text("dialog.task_running_body", message=str(exc)),
            )

    def _apply_status(self, status: TaskStatus):
        if not isinstance(status, TaskStatus):
            return
        text_map = {
            TaskState.IDLE: self.texts.get_text("status.idle"),
            TaskState.RUNNING: self.texts.get_text("status.running"),
            TaskState.SUCCESS: self.texts.get_text("status.success"),
            TaskState.FAILED: self.texts.get_text("status.failed"),
        }
        self.window.status_value.setText(text_map.get(status.state, status.message))
        self.window.site_value.setText(status.site or "-")

    def _task_finished(self, success: bool):
        self.window.start_button.setEnabled(True)
        if not success:
            self.window.status_value.setText(self.texts.get_text("status.failed"))
            QtWidgets.QMessageBox.warning(
                self.window,
                self.texts.get_text("dialog.task_failed_title"),
                self._friendly_runtime_message(self.task_service.get_status().message),
            )

    def _open_output_dir(self):
        self._open_local_path(self.config_service.get_output_dir())

    def _open_log_dir(self):
        self._open_local_path(self.config_service.get_log_dir())

    def _open_local_path(self, path: str):
        Path(path).mkdir(parents=True, exist_ok=True)
        url = QtCore.QUrl.fromLocalFile(path)
        if not QtGui.QDesktopServices.openUrl(url):
            QtWidgets.QMessageBox.warning(
                self.window,
                self.texts.get_text("dialog.open_failed_title"),
                self.texts.get_text("dialog.open_failed_body", path=path),
            )

    def _choose_output_dir(self):
        current_path = self.window.output_root_edit.text().strip()
        selected_dir = QtWidgets.QFileDialog.getExistingDirectory(
            self.window,
            self.texts.get_text("dialog.choose_output_dir_title"),
            current_path or str(Path.home() / "Documents"),
        )
        if selected_dir:
            self.window.output_root_edit.setText(selected_dir)

    def _choose_chrome_path(self):
        current_path = self.window.chrome_path_edit.text().strip()
        selected_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.window,
            self.texts.get_text("dialog.choose_chrome_path_title"),
            str(Path(current_path).parent) if current_path else "/Applications",
        )
        if selected_path:
            self.window.chrome_path_edit.setText(selected_path)

    def _friendly_validation_message(self, raw_message: str, form: TaskForm) -> str:
        lines = [self.texts.get_text(line) for line in raw_message.splitlines() if line.strip()]
        if form.site == "masiro" and form.login_mode == LoginMode.ACCOUNT_PASSWORD:
            lines.append(self.texts.get_text("text.login_hint_masiro_account"))
        return "\n\n".join(lines)

    def _friendly_runtime_message(self, raw_message: str) -> str:
        if "未配置登录信息" in raw_message:
            return self.texts.get_text("dialog.task_failed_no_login")
        if "cookie失效" in raw_message:
            return self.texts.get_text("dialog.task_failed_cookie_invalid")
        if "Chrome" in raw_message or "chrome" in raw_message:
            return self.texts.get_text("dialog.task_failed_chrome_missing")
        if "登录失败" in raw_message:
            return self.texts.get_text("dialog.task_failed_login")
        return self.texts.get_text("dialog.task_failed_generic")

    def _refresh_bookshelf(self):
        site = self._current_site()
        panel = self.window.bookshelf_panel
        books = self.bookshelf_service.list_books(site)
        panel.title_label.setText(self.texts.get_text("text.bookshelf_title_site", site=site))
        panel.subtitle_label.setText(self.texts.get_text("text.bookshelf_subtitle"))
        panel.empty_hint_label.setVisible(not books)
        panel.table.setRowCount(len(books))
        for row, book in enumerate(books):
            self._set_table_item(row, 0, book.custom_name, book.id)
            self._set_table_item(row, 1, book.category or "-", book.id)
            self._set_table_item(row, 2, self._strategy_label(book.update_strategy), book.id)
            self._set_table_item(row, 3, self._format_timestamp(book.updated_at), book.id)
        panel.table.clearSelection()
        panel.table.setCurrentItem(None)
        self._selected_bookshelf_id = None
        self._sync_bookshelf_detail()

    def _set_table_item(self, row: int, column: int, text: str, book_id: int):
        item = QtWidgets.QTableWidgetItem(text)
        item.setData(QtCore.Qt.ItemDataRole.UserRole, book_id)
        self.window.bookshelf_panel.table.setItem(row, column, item)

    def _selected_bookshelf_book(self) -> Optional[BookshelfBook]:
        table = self.window.bookshelf_panel.table
        selected_items = table.selectedItems()
        if not selected_items:
            return None
        book_id = selected_items[0].data(QtCore.Qt.ItemDataRole.UserRole)
        if not book_id:
            return None
        self._selected_bookshelf_id = int(book_id)
        return self.bookshelf_service.get_book(int(book_id))

    def _sync_bookshelf_detail(self):
        panel = self.window.bookshelf_panel
        book = self._selected_bookshelf_book()
        has_selection = book is not None
        for button in (
            panel.edit_button,
            panel.delete_button,
            panel.move_up_button,
            panel.move_down_button,
            panel.fill_task_button,
        ):
            button.setEnabled(has_selection)
        if not has_selection:
            panel.url_value.setText("-")
            panel.category_value.setText("-")
            panel.note_value.setText("-")
            panel.created_value.setText("-")
            panel.updated_value.setText("-")
            return
        panel.url_value.setText(book.url or "-")
        panel.category_value.setText(book.category or "-")
        panel.note_value.setText(book.note or "-")
        panel.created_value.setText(self._format_timestamp(book.created_at))
        panel.updated_value.setText(self._format_timestamp(book.updated_at))

    def _add_bookshelf_book(self):
        site = self._current_site()
        dialog = BookEditorDialog(
            site=site,
            categories=self.bookshelf_service.list_categories(site),
            parent=self.window,
            book=BookshelfBook(
                site=site,
                custom_name=self.window.task_name_edit.text().strip(),
                url=self.window.single_url_edit.text().strip(),
                update_strategy=self._current_update_strategy().value,
                category="",
                note="",
            ),
        )
        dialog.setWindowTitle(self.texts.get_text("button.add"))
        if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        try:
            created = self.bookshelf_service.create_book(dialog.build_book())
        except ValueError as exc:
            QtWidgets.QMessageBox.warning(self.window, self.texts.get_text("dialog.save_to_bookshelf_failed_title"), self.texts.get_text(str(exc), default=str(exc)))
            return
        self._refresh_bookshelf()
        self._select_bookshelf_book(created.id)

    def _edit_bookshelf_book(self):
        book = self._selected_bookshelf_book()
        if book is None:
            return
        dialog = BookEditorDialog(
            site=book.site,
            categories=self.bookshelf_service.list_categories(book.site),
            parent=self.window,
            book=book,
        )
        if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        try:
            updated = self.bookshelf_service.update_book(dialog.build_book())
        except ValueError as exc:
            QtWidgets.QMessageBox.warning(self.window, self.texts.get_text("dialog.update_bookshelf_failed_title"), self.texts.get_text(str(exc), default=str(exc)))
            return
        self._refresh_bookshelf()
        self._select_bookshelf_book(updated.id)

    def _delete_bookshelf_book(self):
        book = self._selected_bookshelf_book()
        if book is None:
            return
        reply = QtWidgets.QMessageBox.question(
            self.window,
            self.texts.get_text("dialog.delete_bookshelf_title"),
            self.texts.get_text("dialog.delete_bookshelf_body", name=book.custom_name),
        )
        if reply != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        self.bookshelf_service.delete_book(book.id)
        self._refresh_bookshelf()

    def _move_bookshelf_book_up(self):
        book = self._selected_bookshelf_book()
        if book is None:
            return
        if self.bookshelf_service.move_up(book.id):
            self._refresh_bookshelf()
            self._select_bookshelf_book(book.id)

    def _move_bookshelf_book_down(self):
        book = self._selected_bookshelf_book()
        if book is None:
            return
        if self.bookshelf_service.move_down(book.id):
            self._refresh_bookshelf()
            self._select_bookshelf_book(book.id)

    def _fill_task_from_bookshelf(self):
        book = self._selected_bookshelf_book()
        if book is None:
            return
        self.window.task_name_edit.setText(book.custom_name)
        self.window.single_url_edit.setText(book.url)
        self._set_task_mode(TaskMode.SINGLE_LINK)
        self._set_update_strategy(UpdateStrategy(book.update_strategy))
        self._refresh_task_mode_ui()
        QtWidgets.QMessageBox.information(
            self.window,
            self.texts.get_text("dialog.fill_task_title"),
            self.texts.get_text("dialog.fill_task_body"),
        )

    def _select_bookshelf_book(self, book_id: Optional[int]):
        if book_id is None:
            return
        table = self.window.bookshelf_panel.table
        for row in range(table.rowCount()):
            item = table.item(row, 0)
            if item and item.data(QtCore.Qt.ItemDataRole.UserRole) == book_id:
                table.selectRow(row)
                table.scrollToItem(item)
                self._selected_bookshelf_id = int(book_id)
                self._sync_bookshelf_detail()
                return

    def _strategy_label(self, update_strategy: str) -> str:
        try:
            return self.texts.get_text(f"strategy.{UpdateStrategy(update_strategy).value}")
        except ValueError:
            return update_strategy

    def _format_timestamp(self, value: str) -> str:
        if not value:
            return "-"
        text = value.replace("T", " ")
        return text.split(".")[0].replace("+00:00", " UTC")

    def _handle_site_changed(self, site: str):
        self._load_site_credentials(site)
        self._refresh_login_ui()

    def _load_site_credentials(self, site: str):
        bundle = self.config_service.load_login_bundle(site)
        self._apply_login_bundle(
            site,
            bundle["login_mode"],
            bundle["username"],
            bundle["password"],
            bundle["cookie"],
            bundle["remember_account"],
            bundle["remember_password"],
        )

    def _apply_login_bundle(
        self,
        site: str,
        login_mode: LoginMode,
        username: str,
        password: str,
        cookie: str,
        remember_account: bool,
        remember_password: bool,
    ):
        _ = site
        self._set_login_mode(login_mode)
        self.window.username_edit.setText(username)
        self.window.password_edit.setText(password)
        self.window.cookie_edit.setPlainText(cookie)
        self._set_checkbox(self.window.remember_account_checkbox, remember_account)
        self._set_checkbox(self.window.remember_password_checkbox, remember_password)

    def _set_checkbox(self, checkbox: QtWidgets.QCheckBox, checked: bool):
        checkbox.blockSignals(True)
        checkbox.setChecked(checked)
        checkbox.blockSignals(False)

    def _handle_remember_account_toggled(self, checked: bool):
        if not checked and self.window.remember_password_checkbox.isChecked():
            self._set_checkbox(self.window.remember_password_checkbox, False)

    def _handle_remember_password_toggled(self, checked: bool):
        if not checked:
            return
        self._set_checkbox(self.window.remember_account_checkbox, True)
        if self.config_service.is_password_storage_available():
            return
        self._set_checkbox(self.window.remember_password_checkbox, False)
        QtWidgets.QMessageBox.information(
            self.window,
            self.texts.get_text("dialog.keychain_unavailable_title"),
            self.texts.get_text("dialog.keychain_unavailable_body"),
        )
