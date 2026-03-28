from __future__ import annotations

from threading import Lock, Thread
from typing import Callable, Optional

from src.app.runtime import run_sync
from src.services.config_service import ConfigService
from src.services.models import TaskForm, TaskState, TaskStatus
from src.utils.log import log


class TaskService:
    def __init__(self, config_service: Optional[ConfigService] = None):
        self.config_service = config_service or ConfigService()
        self._thread: Optional[Thread] = None
        self._lock = Lock()
        self._status = TaskStatus()

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def get_status(self) -> TaskStatus:
        return self._status

    def start_task(
        self,
        form: TaskForm,
        on_log: Optional[Callable[[str], None]] = None,
        on_state: Optional[Callable[[TaskStatus], None]] = None,
        on_finished: Optional[Callable[[bool], None]] = None,
    ):
        with self._lock:
            if self.is_running():
                raise RuntimeError("当前已有任务正在运行。")

            errors = self.config_service.validate_form(form)
            if errors:
                raise ValueError("\n".join(errors))

            worker = Thread(
                target=self._run_task,
                args=(form, on_log, on_state, on_finished),
                daemon=True,
            )
            self._thread = worker
            worker.start()

    def _run_task(
        self,
        form: TaskForm,
        on_log: Optional[Callable[[str], None]],
        on_state: Optional[Callable[[TaskStatus], None]],
        on_finished: Optional[Callable[[bool], None]],
    ):
        unsubscribe = log.subscribe(on_log) if on_log else (lambda: None)
        success = False
        try:
            self._update_state(TaskState.RUNNING, "任务运行中", form.site, on_state)
            runtime_config = self.config_service.save_form(form)
            success = run_sync(config_data=runtime_config, enable_scheduler=False)
            if success:
                self._update_state(TaskState.SUCCESS, "任务已完成", form.site, on_state)
            else:
                self._update_state(TaskState.FAILED, "任务失败，请查看日志", form.site, on_state)
        except Exception as exc:
            log.error(f"任务启动失败: {exc}")
            self._update_state(TaskState.FAILED, str(exc), form.site, on_state)
        finally:
            unsubscribe()
            if on_finished:
                on_finished(success)
            with self._lock:
                self._thread = None

    def _update_state(
        self,
        state: TaskState,
        message: str,
        site: str,
        callback: Optional[Callable[[TaskStatus], None]],
    ):
        self._status = TaskStatus(state=state, message=message, site=site)
        if callback:
            callback(self._status)
