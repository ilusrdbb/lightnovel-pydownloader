import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Optional


class ScrolledFrame(ttk.Frame):

    def __init__(self, parent, **kw):
        super().__init__(parent, **kw)
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient='vertical', command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas)

        self._inner_id = self.canvas.create_window((0, 0), window=self.inner, anchor='nw')
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side='right', fill='y')
        self.canvas.pack(side='left', fill='both', expand=True)

        self.inner.bind('<Configure>', self._on_inner_configure)
        self.canvas.bind('<Configure>', self._on_canvas_configure)

        # 鼠标进入时全局绑定滚轮，离开时解绑，确保子控件不会拦截滚轮事件
        self.canvas.bind('<Enter>', self._on_canvas_enter)
        self.canvas.bind('<Leave>', self._on_canvas_leave)

    def _on_inner_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self._inner_id, width=event.width)

    def _on_canvas_enter(self, event):
        self.canvas.bind_all('<MouseWheel>', self._on_mousewheel, add='+')

    def _on_canvas_leave(self, event):
        self.canvas.unbind_all('<MouseWheel>')

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-event.delta / 8), 'units')


def make_section(parent: ttk.Frame, label: str) -> ttk.LabelFrame:
    """创建分组标题行。"""
    frame = ttk.LabelFrame(parent, text=label)
    frame.pack(fill='x', padx=8, pady=(8, 4))
    return frame


def make_field_row(parent: ttk.Frame, label: str, tooltip: str = '') -> ttk.Frame:
    """创建配置字段的标签行框架。"""
    frame = ttk.Frame(parent)
    frame.pack(fill='x', padx=16, pady=3)
    lbl = ttk.Label(frame, text=label, width=16, anchor='e')
    lbl.pack(side='left', padx=(0, 8))
    if tooltip:
        lbl.configure(text=f'{label} (?)')
        _set_tooltip(lbl, tooltip)
    return frame


def make_str_widget(row: ttk.Frame, value: str = '') -> tk.StringVar:
    """单行文本输入。"""
    var = tk.StringVar(value=str(value) if value else '')
    entry = ttk.Entry(row, textvariable=var)
    entry.pack(side='left', fill='x', expand=True, padx=(0, 8))
    return var


def make_int_widget(row: ttk.Frame, value: int = 0,
                    min_val: int = 0, max_val: int = 9999) -> tk.StringVar:
    """数字输入（以字符串存储，保存时校验）。"""
    var = tk.StringVar(value=str(value))
    entry = ttk.Entry(row, textvariable=var, width=10)
    entry.pack(side='left', padx=(0, 8))

    def validate(P):
        if P == '' or P == '-':
            return True
        return P.isdigit()

    vcmd = entry.register(validate)
    entry.configure(validate='key', validatecommand=(vcmd, '%P'))
    return var


def make_bool_widget(row: ttk.Frame, value: bool = False) -> tk.BooleanVar:
    """复选框。"""
    var = tk.BooleanVar(value=bool(value))
    cb = ttk.Checkbutton(row, variable=var)
    cb.pack(side='left', padx=(0, 8))
    return var


def make_select_widget(row: ttk.Frame, options: List[str],
                       value: str = '') -> tk.StringVar:
    """下拉选择框。"""
    var = tk.StringVar(value=str(value) if value else '')
    cb = ttk.Combobox(row, textvariable=var, values=options, state='readonly', width=18)
    cb.pack(side='left', padx=(0, 8))
    if not value and options:
        cb.set(options[0])
    return var


def make_multiselect_widget(row: ttk.Frame, options: List[str],
                            selected: List[str]) -> List[tuple]:
    """多选复选框组。返回 [(label, BooleanVar), ...]。"""
    vars_list = []
    selected_set = set(selected) if selected else set()
    frame = ttk.Frame(row)
    frame.pack(side='left', fill='x', expand=True)
    for opt in options:
        bv = tk.BooleanVar(value=(opt in selected_set))
        cb = ttk.Checkbutton(frame, text=opt, variable=bv)
        cb.pack(side='left', padx=(0, 8))
        vars_list.append((opt, bv))
    return vars_list


def make_text_list_widget(row: ttk.Frame, items: List[str]) -> tk.Text:
    """列表值的多行文本输入（每行一个）。"""
    return _make_text_area(row,
                           '\n'.join(str(i) for i in items) if items else '',
                           height=4)


def make_text_dict_widget(row: ttk.Frame, data: Dict) -> tk.Text:
    """字典值的多行文本输入（每行 key: value）。"""
    lines = []
    if data:
        for k, v in data.items():
            lines.append(f'{k}: {v}')
    return _make_text_area(row, '\n'.join(lines), height=3)


def make_readonly_text(row: ttk.Frame, text: str) -> tk.Text:
    """只读多行文本显示。"""
    text_widget = tk.Text(row, height=6, wrap='word', font=('Consolas', 8))
    text_widget.insert('1.0', text)
    text_widget.configure(state='disabled')
    text_widget.pack(side='left', fill='x', expand=True, padx=(0, 8))
    return text_widget


def _make_text_area(row: ttk.Frame, content: str,
                    height: int = 4) -> tk.Text:
    """共享辅助函数：在行中创建可滚动的文本区域。"""
    container = ttk.Frame(row)
    container.pack(side='left', fill='x', expand=True, padx=(0, 8))

    text_widget = tk.Text(container, height=height, width=40, wrap='word')
    sb = ttk.Scrollbar(container, orient='vertical', command=text_widget.yview)
    text_widget.configure(yscrollcommand=sb.set)

    text_widget.pack(side='left', fill='both', expand=True)
    sb.pack(side='right', fill='y')

    if content:
        text_widget.insert('1.0', content)

    return text_widget


def _set_tooltip(widget: ttk.Label, text: str):
    """鼠标悬停时显示简单提示。"""
    tip: Optional[tk.Toplevel] = None

    def show(event):
        nonlocal tip
        if tip:
            return
        x = event.x_root + 12
        y = event.y_root + 12
        tip = tk.Toplevel(widget)
        tip.wm_overrideredirect(True)
        tip.wm_geometry(f'+{x}+{y}')
        ttk.Label(tip, text=text, background='#ffffcc', relief='solid',
                  borderwidth=1, wraplength=300).pack()
        tip.bind('<Leave>', hide)

    def hide(event=None):
        nonlocal tip
        if tip:
            tip.destroy()
            tip = None

    widget.bind('<Enter>', show)
    widget.bind('<Leave>', hide)
