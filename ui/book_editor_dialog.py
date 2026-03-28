from __future__ import annotations

from PySide6 import QtWidgets

from src.bookshelf.models import BookshelfBook
from src.services.models import UpdateStrategy
from src.services.text_catalog import get_text_catalog

TEXTS = get_text_catalog()


class BookEditorDialog(QtWidgets.QDialog):
    def __init__(
        self,
        site: str,
        categories: list[str],
        parent: QtWidgets.QWidget | None = None,
        book: BookshelfBook | None = None,
    ):
        super().__init__(parent)
        self.site = site
        self.book = book
        self.setWindowTitle(TEXTS.get_text("button.edit") if book else TEXTS.get_text("button.add"))
        self.resize(520, 380)
        self._build_ui(categories)
        if book:
            self._load_book(book)

    def _build_ui(self, categories: list[str]):
        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()

        self.site_value = QtWidgets.QLabel(self.site)
        self.name_edit = QtWidgets.QLineEdit()
        self.name_edit.setPlaceholderText(TEXTS.get_text("placeholder.book_name"))
        self.url_edit = QtWidgets.QLineEdit()
        self.url_edit.setPlaceholderText(TEXTS.get_text("placeholder.book_url"))
        self.strategy_combo = QtWidgets.QComboBox()
        for strategy in UpdateStrategy:
            self.strategy_combo.addItem(TEXTS.get_text(f"strategy.{strategy.value}"), strategy.value)
        self.category_combo = QtWidgets.QComboBox()
        self.category_combo.setEditable(True)
        self.category_combo.addItems(categories)
        self.category_combo.setInsertPolicy(QtWidgets.QComboBox.InsertPolicy.NoInsert)
        self.note_edit = QtWidgets.QPlainTextEdit()
        self.note_edit.setPlaceholderText(TEXTS.get_text("placeholder.book_note"))
        self.note_edit.setFixedHeight(110)

        form.addRow(TEXTS.get_text("label.site"), self.site_value)
        form.addRow(TEXTS.get_text("label.bookshelf_name"), self.name_edit)
        form.addRow(TEXTS.get_text("label.bookshelf_url"), self.url_edit)
        form.addRow(TEXTS.get_text("label.update_strategy"), self.strategy_combo)
        form.addRow(TEXTS.get_text("label.bookshelf_category"), self.category_combo)
        form.addRow(TEXTS.get_text("label.bookshelf_note"), self.note_edit)
        layout.addLayout(form)

        hint = QtWidgets.QLabel(TEXTS.get_text("text.book_editor_hint"))
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #666;")
        layout.addWidget(hint)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._handle_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_book(self, book: BookshelfBook):
        self.name_edit.setText(book.custom_name)
        self.url_edit.setText(book.url)
        index = self.strategy_combo.findData(book.update_strategy)
        if index >= 0:
            self.strategy_combo.setCurrentIndex(index)
        if book.category:
            category_index = self.category_combo.findText(book.category)
            if category_index >= 0:
                self.category_combo.setCurrentIndex(category_index)
            else:
                self.category_combo.setEditText(book.category)
        self.note_edit.setPlainText(book.note)

    def _handle_accept(self):
        if not self.name_edit.text().strip():
            QtWidgets.QMessageBox.warning(
                self,
                TEXTS.get_text("dialog.missing_name_title"),
                TEXTS.get_text("validation.bookshelf_name_required"),
            )
            return
        if not self.url_edit.text().strip():
            QtWidgets.QMessageBox.warning(
                self,
                TEXTS.get_text("dialog.missing_url_title"),
                TEXTS.get_text("validation.bookshelf_url_required"),
            )
            return
        self.accept()

    def build_book(self) -> BookshelfBook:
        return BookshelfBook(
            id=self.book.id if self.book else None,
            site=self.site,
            custom_name=self.name_edit.text().strip(),
            url=self.url_edit.text().strip(),
            update_strategy=str(self.strategy_combo.currentData()),
            category=self.category_combo.currentText().strip(),
            note=self.note_edit.toPlainText().strip(),
            sort_order=self.book.sort_order if self.book else 0,
            created_at=self.book.created_at if self.book else "",
            updated_at=self.book.updated_at if self.book else "",
            import_source=self.book.import_source if self.book else "",
            import_payload_json=self.book.import_payload_json if self.book else "",
            extra_json=self.book.extra_json if self.book else "",
        )
