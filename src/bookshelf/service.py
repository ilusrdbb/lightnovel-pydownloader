from __future__ import annotations

from typing import List, Optional

from src.bookshelf.models import BookshelfBook
from src.bookshelf.repository import BookshelfRepository
from src.services.models import SUPPORTED_SITES, UpdateStrategy


class BookshelfService:
    def __init__(self, repository: Optional[BookshelfRepository] = None):
        self.repository = repository or BookshelfRepository()

    def list_books(self, site: str) -> List[BookshelfBook]:
        self._validate_site(site)
        return self.repository.list_books(site)

    def list_categories(self, site: str) -> List[str]:
        self._validate_site(site)
        return self.repository.list_categories(site)

    def get_book(self, book_id: int) -> Optional[BookshelfBook]:
        return self.repository.get_book(book_id)

    def create_book(self, book: BookshelfBook) -> BookshelfBook:
        self._validate_book(book)
        return self.repository.create_book(book)

    def update_book(self, book: BookshelfBook) -> BookshelfBook:
        if book.id is None:
            raise ValueError("编辑书库记录时缺少记录 id。")
        self._validate_book(book)
        return self.repository.update_book(book)

    def delete_book(self, book_id: int):
        self.repository.delete_book(book_id)

    def move_up(self, book_id: int) -> bool:
        return self.repository.move_book(book_id, "up")

    def move_down(self, book_id: int) -> bool:
        return self.repository.move_book(book_id, "down")

    def _validate_book(self, book: BookshelfBook):
        self._validate_site(book.site)
        if not book.custom_name.strip():
            raise ValueError("书库记录需要填写名称。")
        if not book.url.strip():
            raise ValueError("书库记录需要填写小说链接。")
        if book.update_strategy not in {strategy.value for strategy in UpdateStrategy}:
            raise ValueError("书库记录的更新策略无效。")

    def _validate_site(self, site: str):
        if site not in SUPPORTED_SITES:
            raise ValueError("书库记录的站点无效。")
