from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets

from src.services.config_service import ConfigService
from src.services.models import LoginMode, TaskForm, TaskMode, TaskState, TaskStatus
from src.services.task_service import TaskService
from ui.main_window import MainWindow


class MainController(QtCore.QObject):
    log_signal = QtCore.Signal(str)
    state_signal = QtCore.Signal(object)
    finished_signal = QtCore.Signal(bool)

    def __init__(self):
        super().__init__()
        self.config_service = ConfigService()
        self.task_service = TaskService(self.config_service)
        self.window = MainWindow()

        self.log_signal.connect(self.window.log_text.appendPlainText)
        self.state_signal.connect(self._apply_status)
        self.finished_signal.connect(self._task_finished)

        self.window.site_combo.currentIndexChanged.connect(self._refresh_login_ui)
        self.window.task_mode_combo.currentIndexChanged.connect(self._refresh_task_mode_ui)
        self.window.login_mode_combo.currentIndexChanged.connect(self._refresh_login_ui)
        self.window.purchase_checkbox.toggled.connect(self._refresh_login_ui)
        self.window.start_button.clicked.connect(self._start_task)
        self.window.open_output_button.clicked.connect(self._open_output_dir)
        self.window.open_log_button.clicked.connect(self._open_log_dir)

        self._load_initial_form()
        self._refresh_task_mode_ui()
        self._refresh_login_ui()

    def show(self):
        self.window.show()

    def _load_initial_form(self):
        form = self.config_service.load_form()
        self.window.site_combo.setCurrentText(form.site)
        self._set_task_mode(form.task_mode)
        self.window.single_url_edit.setText(form.single_url)
        self.window.start_page_spin.setValue(form.start_page)
        self.window.end_page_spin.setValue(form.end_page)
        self._set_login_mode(form.login_mode)
        self.window.username_edit.setText(form.username)
        self.window.password_edit.setText(form.password)
        self.window.cookie_edit.setPlainText(form.cookie)
        self.window.purchase_checkbox.setChecked(form.is_purchase)
        self.window.max_purchase_spin.setValue(form.max_purchase)
        self.window.convert_hans_checkbox.setChecked(form.convert_hans)
        self.window.proxy_edit.setText(form.proxy_url)
        self.window.convert_txt_checkbox.setChecked(form.convert_txt)
        self.window.site_value.setText(form.site)

    def _set_task_mode(self, task_mode: TaskMode):
        index = self.window.task_mode_combo.findData(task_mode.value)
        if index >= 0:
            self.window.task_mode_combo.setCurrentIndex(index)

    def _set_login_mode(self, login_mode: LoginMode):
        index = self.window.login_mode_combo.findData(login_mode.value)
        if index >= 0:
            self.window.login_mode_combo.setCurrentIndex(index)

    def _current_task_mode(self) -> TaskMode:
        return TaskMode(self.window.task_mode_combo.currentData())

    def _current_login_mode(self) -> LoginMode:
        return LoginMode(self.window.login_mode_combo.currentData())

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

    def _refresh_login_ui(self):
        site = self._current_site()
        login_mode = self._current_login_mode()

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
                self.window.login_hint_label.setText("真白萌使用账号密码登录时，可能需要本机可用的 Chrome。")
                self.window.login_hint_label.show()
            else:
                self.window.login_hint_label.hide()

        purchase_supported = site in ("lk", "masiro")
        self.window.purchase_checkbox.setEnabled(purchase_supported)
        self.window.max_purchase_spin.setEnabled(purchase_supported and self.window.purchase_checkbox.isChecked())
        self.window.site_value.setText(site)

    def _collect_form(self) -> TaskForm:
        site = self._current_site()
        login_mode = self._current_login_mode() if site in ("esj", "masiro") else (
            LoginMode.ACCOUNT_PASSWORD if site == "lk" else LoginMode.COOKIE
        )
        return TaskForm(
            site=site,
            task_mode=self._current_task_mode(),
            single_url=self.window.single_url_edit.text().strip(),
            start_page=self.window.start_page_spin.value(),
            end_page=self.window.end_page_spin.value(),
            login_mode=login_mode,
            username=self.window.username_edit.text().strip(),
            password=self.window.password_edit.text(),
            cookie=self.window.cookie_edit.toPlainText().strip(),
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
            QtWidgets.QMessageBox.warning(self.window, "表单未完成", str(exc))
        except RuntimeError as exc:
            QtWidgets.QMessageBox.information(self.window, "任务进行中", str(exc))

    def _apply_status(self, status: TaskStatus):
        if not isinstance(status, TaskStatus):
            return
        text_map = {
            TaskState.IDLE: "空闲",
            TaskState.RUNNING: "运行中",
            TaskState.SUCCESS: "已完成",
            TaskState.FAILED: "失败",
        }
        self.window.status_value.setText(text_map.get(status.state, status.message))
        self.window.site_value.setText(status.site or "-")

    def _task_finished(self, success: bool):
        self.window.start_button.setEnabled(True)
        if not success:
            self.window.status_value.setText("失败")

    def _open_output_dir(self):
        self._open_local_path(self.config_service.get_output_dir())

    def _open_log_dir(self):
        self._open_local_path(self.config_service.get_log_dir())

    def _open_local_path(self, path: str):
        Path(path).mkdir(parents=True, exist_ok=True)
        url = QtCore.QUrl.fromLocalFile(path)
        if not QtGui.QDesktopServices.openUrl(url):
            QtWidgets.QMessageBox.warning(self.window, "打开失败", f"无法打开目录：{path}")
