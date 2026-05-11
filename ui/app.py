import os
import queue
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk

from ruamel.yaml import YAML

_yaml = YAML()
_yaml.preserve_quotes = True
_yaml.width = 4096

from ui.fields import CONFIG_FIELDS, ADVANCE_FIELDS, LOGIN_SITE_FIELDS
from ui.widgets import (
    ScrolledFrame,
    make_section,
    make_field_row,
    make_str_widget,
    make_int_widget,
    make_bool_widget,
    make_select_widget,
    make_multiselect_widget,
    make_text_list_widget,
    make_text_dict_widget,
)

from src.core.constants import VERSION, GUI_POLL_INTERVAL, SITES

if getattr(sys, 'frozen', False):
    _PROJECT_ROOT = os.path.dirname(sys.executable)
else:
    _UI_ROOT = os.path.dirname(os.path.abspath(__file__))
    _PROJECT_ROOT = os.path.dirname(_UI_ROOT)


class ConfigForm:

    def __init__(self, parent: ttk.Frame, fields: list, yaml_path: str):
        self.fields = fields
        self.yaml_path = yaml_path
        self.data: dict = {}
        self._vars: dict = {}

        self._load()
        self.scrolled = ScrolledFrame(parent)
        self.scrolled.pack(fill='both', expand=True)
        self._build()

    def _load(self):
        src = self.yaml_path
        if not os.path.exists(src) and getattr(sys, 'frozen', False):
            bundled = os.path.join(sys._MEIPASS, os.path.basename(src))
            if os.path.exists(bundled):
                shutil.copy2(bundled, src)
        with open(src, 'r', encoding='utf-8') as f:
            self.data = _yaml.load(f) or {}

    def save(self):
        self._collect()
        with open(self.yaml_path, 'w', encoding='utf-8') as f:
            _yaml.dump(self.data, f)

    def reload(self):
        self._load()
        self._update_vars()

    def _update_vars(self):
        for entry_key, (kind, path, ref) in self._vars.items():
            cur = self._get_value(path)
            if kind == 'str':
                ref.set(str(cur) if cur else '')
            elif kind == 'int':
                ref.set(str(cur) if cur is not None else '')
            elif kind == 'bool':
                ref.set(bool(cur))
            elif kind == 'multiselect':
                selected_set = set(cur) if isinstance(cur, list) else set()
                for label, bv in ref:
                    bv.set(label in selected_set)
            elif kind == 'text_list':
                ref.delete('1.0', 'end')
                if isinstance(cur, list):
                    ref.insert('1.0', '\n'.join(str(i) for i in cur))
            elif kind == 'text_dict':
                ref.delete('1.0', 'end')
                if isinstance(cur, dict):
                    lines = [f'{k}: {v}' for k, v in cur.items()]
                    ref.insert('1.0', '\n'.join(lines))

    def _get_value(self, path: tuple):
        cur = self.data
        for key in path:
            if isinstance(cur, dict):
                cur = cur.get(key)
            else:
                return None
        return cur

    def _set_value(self, path: tuple, value):
        cur = self.data
        for key in path[:-1]:
            if key not in cur or not isinstance(cur[key], dict):
                cur[key] = {}
            cur = cur[key]
        cur[path[-1]] = value

    def _build(self):
        inner = self.scrolled.inner
        for entry in self.fields:
            kind, key, label, widget, extra = entry
            if kind == 'field':
                row = make_field_row(inner, label, extra.get('tooltip', ''))
                self._make_field(row, key, widget, extra)
            elif kind == 'login_info':
                self._make_login_info(inner)
            elif kind == 'scheduler':
                self._make_scheduler(inner)
            elif kind == 'calibre':
                self._make_calibre(inner)
            elif kind == 'domain':
                self._make_domain(inner)

    def _make_field(self, row: ttk.Frame, key: str, widget: str, extra: dict):
        path = (key,)
        cur = self.data.get(key)

        if widget == 'str':
            v = cur if isinstance(cur, str) else extra.get('default', '')
            var = make_str_widget(row, v)
            self._vars[key] = ('str', path, var)

        elif widget == 'int':
            default = extra.get('default', 0)
            v = cur if isinstance(cur, int) else default
            var = make_int_widget(row, v, extra.get('min', 0), extra.get('max', 9999))
            self._vars[key] = ('int', path, var)

        elif widget == 'bool':
            v = cur if isinstance(cur, bool) else extra.get('default', False)
            var = make_bool_widget(row, v)
            self._vars[key] = ('bool', path, var)

        elif widget == 'select':
            options = extra.get('options', [])
            v = cur if isinstance(cur, str) else extra.get('default', '')
            var = make_select_widget(row, options, v)
            self._vars[key] = ('str', path, var)

        elif widget == 'multiselect':
            options = extra.get('options', [])
            selected = cur if isinstance(cur, list) else extra.get('default', [])
            vars_list = make_multiselect_widget(row, options, selected)
            self._vars[key] = ('multiselect', path, vars_list)

        elif widget == 'text_list':
            items = cur if isinstance(cur, list) else []
            text_w = make_text_list_widget(row, items)
            self._vars[key] = ('text_list', path, text_w)

        elif widget == 'text_dict':
            d = cur if isinstance(cur, dict) else {}
            text_w = make_text_dict_widget(row, d)
            self._vars[key] = ('text_dict', path, text_w)

    def _make_login_info(self, parent: ttk.Frame):
        for site, field_names in LOGIN_SITE_FIELDS.items():
            section = make_section(parent, f'{site} 登录')
            for field_name in field_names:
                row = make_field_row(section, field_name, '')
                cur = self._get_value(('login_info', site, field_name)) or ''
                var = make_str_widget(row, cur)
                self._vars[f'login_info.{site}.{field_name}'] = (
                    'str', ('login_info', site, field_name), var)

    def _make_scheduler(self, parent: ttk.Frame):
        row = make_field_row(parent, '定时执行', '')
        enabled = self._get_value(('scheduler_config', 'enabled'))
        hour = self._get_value(('scheduler_config', 'hour'))
        minute = self._get_value(('scheduler_config', 'minute'))

        bv = tk.BooleanVar(value=bool(enabled))
        ttk.Checkbutton(row, text='启用', variable=bv).pack(side='left', padx=(0, 8))
        self._vars['scheduler._enabled'] = ('bool', ('scheduler_config', 'enabled'), bv)

        ttk.Label(row, text=' 时:').pack(side='left')
        hv = tk.StringVar(value=str(hour) if hour is not None else '9')
        ttk.Entry(row, textvariable=hv, width=4).pack(side='left', padx=(0, 8))
        self._vars['scheduler._hour'] = ('int', ('scheduler_config', 'hour'), hv)

        ttk.Label(row, text='分:').pack(side='left')
        mv = tk.StringVar(value=str(minute) if minute is not None else '30')
        ttk.Entry(row, textvariable=mv, width=4).pack(side='left')
        self._vars['scheduler._minute'] = ('int', ('scheduler_config', 'minute'), mv)

    def _make_calibre(self, parent: ttk.Frame):
        section = make_section(parent, 'Calibre推送')
        row = make_field_row(section, '', '')
        enabled = self._get_value(('push_calibre', 'enabled'))
        bv = tk.BooleanVar(value=bool(enabled))
        ttk.Checkbutton(row, text='启用', variable=bv).pack(side='left', padx=(0, 8))
        self._vars['calibre._enabled'] = ('bool', ('push_calibre', 'enabled'), bv)

        tooltips = {
            'container_name': 'calibre-web容器名称或容器id',
            'absolute_path': '爬虫的epub目录 填docker映射路径而不是真实路径 需要先在calibre-web中额外映射爬虫的epub目录',
            'library_path': '书籍目录 填docker映射路径而不是真实路径',
        }
        for key, label in [
            ('container_name', '容器名称'),
            ('absolute_path', '容器epub路径'),
            ('library_path', '容器书库路径'),
        ]:
            r = make_field_row(section, label, tooltips.get(key, ''))
            cur = self._get_value(('push_calibre', key)) or ''
            var = make_str_widget(r, cur)
            self._vars[f'calibre._{key}'] = ('str', ('push_calibre', key), var)

    def _make_domain(self, parent: ttk.Frame):
        section = make_section(parent, '站点域名')
        for site in SITES:
            row = make_field_row(section, site, '')
            cur = self._get_value(('domain', site)) or ''
            var = make_str_widget(row, cur)
            self._vars[f'domain._{site}'] = ('str', ('domain', site), var)

    def _collect(self):
        for _entry_key, (kind, path, ref) in self._vars.items():
            if kind == 'str':
                self._set_value(path, ref.get())
            elif kind == 'int':
                try:
                    self._set_value(path, int(ref.get()))
                except (ValueError, TypeError):
                    pass
            elif kind == 'bool':
                self._set_value(path, ref.get())
            elif kind == 'multiselect':
                self._set_value(path, [label for label, bv in ref if bv.get()])
            elif kind == 'text_list':
                content = ref.get('1.0', 'end-1c')
                self._set_value(path, [l.strip() for l in content.splitlines()
                                       if l.strip()])
            elif kind == 'text_dict':
                d = {}
                for line in ref.get('1.0', 'end-1c').splitlines():
                    line = line.strip()
                    if ':' in line:
                        k, v = line.split(':', 1)
                        d[k.strip()] = v.strip()
                self._set_value(path, d)


class LogPanel(ttk.Frame):

    def __init__(self, parent: ttk.Frame):
        super().__init__(parent)
        self.pack(fill='both', expand=True)

        self.text = tk.Text(self, wrap='word', state='disabled',
                            font=('Consolas', 9))
        sb = ttk.Scrollbar(self, orient='vertical', command=self.text.yview)
        self.text.configure(yscrollcommand=sb.set)

        sb.pack(side='right', fill='y')
        self.text.pack(side='left', fill='both', expand=True)

    def append(self, line: str):
        self.text.configure(state='normal')
        self.text.insert('end', line)
        self.text.see('end')
        self.text.configure(state='disabled')

    def clear(self):
        self.text.configure(state='normal')
        self.text.delete('1.0', 'end')
        self.text.configure(state='disabled')


class Runner:

    def __init__(self, log_queue: queue.Queue, project_root: str):
        self.log_queue = log_queue
        self.project_root = project_root
        self.process: subprocess.Popen | None = None
        self._running = False

    def start(self):
        self._running = True
        if getattr(sys, 'frozen', False):
            base = os.path.dirname(sys.executable)
            cli = os.path.join(base, 'lightnovel.exe')
            cmd = [cli]
        else:
            cmd = [sys.executable, os.path.join(self.project_root, 'lightnovel.py')]

        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            cwd=self.project_root,
            bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
        )
        t = threading.Thread(target=self._read_loop, daemon=True)
        t.start()

    def _read_loop(self):
        for line in iter(self.process.stdout.readline, ''):
            if line:
                self.log_queue.put(line)
        self.process.stdout.close()
        ret = self.process.wait()
        self.log_queue.put(f'\n--- 程序退出，返回码: {ret} ---\n')
        self._running = False

    def stop(self):
        if self.process:
            self.process.terminate()
            self.process = None
        self._running = False

    def is_running(self) -> bool:
        return self._running


class MainApp:

    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f'lightnovel-pydownloader v{VERSION}')
        self.root.geometry('720x540')
        self.root.minsize(480, 360)

        style = ttk.Style()
        style.theme_use('vista' if 'vista' in style.theme_names() else 'default')

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=8, pady=(8, 0))

        # 基本配置标签页
        tab_config = ttk.Frame(self.notebook)
        self.notebook.add(tab_config, text='基本配置')
        self.config_form = ConfigForm(
            tab_config, CONFIG_FIELDS,
            os.path.join(_PROJECT_ROOT, 'config.yaml'))

        # 高级配置标签页
        tab_advance = ttk.Frame(self.notebook)
        self.notebook.add(tab_advance, text='高级配置')
        self.advance_form = ConfigForm(
            tab_advance, ADVANCE_FIELDS,
            os.path.join(_PROJECT_ROOT, 'advance.yaml'))

        # 运行日志标签页
        tab_log = ttk.Frame(self.notebook)
        self.notebook.add(tab_log, text='运行日志')
        self.log_panel = LogPanel(tab_log)

        # 底部按钮栏
        bottom = ttk.Frame(self.root)
        bottom.pack(fill='x', padx=8, pady=8)

        self.save_btn = ttk.Button(bottom, text='保存配置', command=self._save)
        self.save_btn.pack(side='left', padx=(0, 6))

        self.reset_btn = ttk.Button(bottom, text='重置', command=self._reset)
        self.reset_btn.pack(side='left', padx=(0, 6))

        self.run_btn = ttk.Button(bottom, text='▶ 运行', command=self._run)
        self.run_btn.pack(side='left', padx=(0, 6))

        self.stop_btn = ttk.Button(bottom, text='■ 停止', command=self._stop,
                                   state='disabled')
        self.stop_btn.pack(side='left')

        self.status_lbl = ttk.Label(bottom, text='就绪')
        self.status_lbl.pack(side='right')

        self.runner: Runner | None = None
        self._log_queue: queue.Queue | None = None

        self.root.protocol('WM_DELETE_WINDOW', self._on_close)

    def _save(self):
        # 备份当前文件
        for yaml_file in ('config.yaml', 'advance.yaml'):
            src = os.path.join(_PROJECT_ROOT, yaml_file)
            dst = os.path.join(_PROJECT_ROOT, yaml_file + '.bak')
            if os.path.exists(src):
                shutil.copy2(src, dst)
        self.config_form.save()
        self.advance_form.save()
        self.status_lbl.config(text='配置已保存')

    def _reset(self):
        restored = False
        for yaml_file in ('config.yaml', 'advance.yaml'):
            src = os.path.join(_PROJECT_ROOT, yaml_file + '.bak')
            dst = os.path.join(_PROJECT_ROOT, yaml_file)
            if os.path.exists(src):
                shutil.copy2(src, dst)
                restored = True
        if restored:
            self.config_form.reload()
            self.advance_form.reload()
            self.status_lbl.config(text='已重置到上次保存前的状态')
        else:
            self.status_lbl.config(text='没有备份文件，无法重置')

    def _run(self):
        # 运行前始终先保存
        self._save()
        self.log_panel.clear()
        # 切换到日志标签页
        self.notebook.select(2)
        self.run_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.status_lbl.config(text='运行中…')

        self._log_queue = queue.Queue()
        self.runner = Runner(self._log_queue, _PROJECT_ROOT)
        self.runner.start()
        self._poll_log()

    def _poll_log(self):
        if self._log_queue:
            while True:
                try:
                    line = self._log_queue.get_nowait()
                    self.log_panel.append(line)
                except queue.Empty:
                    break

        if self.runner and self.runner.is_running():
            self.root.after(GUI_POLL_INTERVAL, self._poll_log)
        else:
            # 读取完剩余日志行再标记完成
            if self._log_queue:
                while True:
                    try:
                        self.log_panel.append(self._log_queue.get_nowait())
                    except queue.Empty:
                        break
            self._on_done()

    def _on_done(self):
        self.run_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.status_lbl.config(text='已完成')

    def _stop(self):
        if self.runner:
            self.runner.stop()
        self._on_done()

    def _on_close(self):
        if self.runner and self.runner.is_running():
            self.runner.stop()
        self.root.destroy()

    def launch(self):
        self.root.mainloop()


def launch():
    """启动GUI配置编辑器，可从任意入口脚本安全调用。"""
    app = MainApp()
    app.launch()


if __name__ == '__main__':
    launch()
