from __future__ import annotations

from PySide6 import QtCore, QtWidgets
from src.services.text_catalog import get_text_catalog

TEXTS = get_text_catalog()


class BookshelfPanel(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(10)

        header_row = QtWidgets.QHBoxLayout()
        self.title_label = QtWidgets.QLabel(TEXTS.get_text("group.bookshelf"))
        self.title_label.setStyleSheet("font-weight: 600; font-size: 16px;")
        header_row.addWidget(self.title_label)
        header_row.addStretch()
        layout.addLayout(header_row)

        self.subtitle_label = QtWidgets.QLabel(TEXTS.get_text("text.bookshelf_subtitle"))
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setStyleSheet("color: #666;")
        layout.addWidget(self.subtitle_label)

        button_row = QtWidgets.QHBoxLayout()
        self.add_button = QtWidgets.QPushButton(TEXTS.get_text("button.add"))
        self.edit_button = QtWidgets.QPushButton(TEXTS.get_text("button.edit"))
        self.delete_button = QtWidgets.QPushButton(TEXTS.get_text("button.delete"))
        self.move_up_button = QtWidgets.QPushButton(TEXTS.get_text("button.move_up"))
        self.move_down_button = QtWidgets.QPushButton(TEXTS.get_text("button.move_down"))
        self.fill_task_button = QtWidgets.QPushButton(TEXTS.get_text("button.fill_task"))
        for button in (
            self.add_button,
            self.edit_button,
            self.delete_button,
            self.move_up_button,
            self.move_down_button,
            self.fill_task_button,
        ):
            button_row.addWidget(button)
        button_row.addStretch()
        layout.addLayout(button_row)

        self.empty_hint_label = QtWidgets.QLabel(TEXTS.get_text("text.bookshelf_empty"))
        self.empty_hint_label.setWordWrap(True)
        self.empty_hint_label.setStyleSheet("color: #666;")
        layout.addWidget(self.empty_hint_label)

        self.table = QtWidgets.QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            [
                TEXTS.get_text("label.bookshelf_name"),
                TEXTS.get_text("label.bookshelf_category"),
                TEXTS.get_text("label.update_strategy"),
                TEXTS.get_text("label.bookshelf_updated_at"),
            ]
        )
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table, 1)

        detail_group = QtWidgets.QGroupBox(TEXTS.get_text("group.bookshelf_detail"))
        detail_layout = QtWidgets.QFormLayout(detail_group)
        self.url_value = QtWidgets.QLabel("-")
        self.url_value.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        self.url_value.setWordWrap(True)
        self.category_value = QtWidgets.QLabel("-")
        self.note_value = QtWidgets.QLabel("-")
        self.note_value.setWordWrap(True)
        self.note_value.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        self.created_value = QtWidgets.QLabel("-")
        self.updated_value = QtWidgets.QLabel("-")
        detail_layout.addRow(TEXTS.get_text("label.bookshelf_url"), self.url_value)
        detail_layout.addRow(TEXTS.get_text("label.bookshelf_category"), self.category_value)
        detail_layout.addRow(TEXTS.get_text("label.bookshelf_note"), self.note_value)
        detail_layout.addRow(TEXTS.get_text("label.bookshelf_created_at"), self.created_value)
        detail_layout.addRow(TEXTS.get_text("label.bookshelf_updated_at"), self.updated_value)
        layout.addWidget(detail_group)
