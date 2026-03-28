from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, List, Optional

from src.bookshelf.models import BookshelfBook
from src.utils.paths import get_bookshelf_db_path


_SCHEMA_VERSION = "1"


class BookshelfRepository:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path or get_bookshelf_db_path())
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _initialize(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site TEXT NOT NULL,
                    custom_name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    update_strategy TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT '',
                    note TEXT NOT NULL DEFAULT '',
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    import_source TEXT NOT NULL DEFAULT '',
                    import_payload_json TEXT NOT NULL DEFAULT '',
                    extra_json TEXT NOT NULL DEFAULT ''
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_books_site_sort
                ON books(site, sort_order, id)
                """
            )
            conn.execute(
                """
                INSERT INTO meta(key, value)
                VALUES('schema_version', ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
                """,
                (_SCHEMA_VERSION,),
            )

    def list_books(self, site: str) -> List[BookshelfBook]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM books
                WHERE site = ?
                ORDER BY sort_order ASC, id ASC
                """,
                (site,),
            ).fetchall()
        return [self._row_to_book(row) for row in rows]

    def list_categories(self, site: str) -> List[str]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT category
                FROM books
                WHERE site = ? AND category != ''
                ORDER BY category COLLATE NOCASE ASC
                """,
                (site,),
            ).fetchall()
        return [str(row["category"]) for row in rows]

    def get_book(self, book_id: int) -> Optional[BookshelfBook]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM books WHERE id = ?",
                (book_id,),
            ).fetchone()
        return self._row_to_book(row) if row else None

    def create_book(self, book: BookshelfBook) -> BookshelfBook:
        now = self._now()
        with self._connect() as conn:
            sort_order = book.sort_order or self._next_sort_order(conn, book.site)
            cursor = conn.execute(
                """
                INSERT INTO books(
                    site, custom_name, url, update_strategy, category, note,
                    sort_order, created_at, updated_at, import_source,
                    import_payload_json, extra_json
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    book.site,
                    book.custom_name,
                    book.url,
                    book.update_strategy,
                    book.category,
                    book.note,
                    sort_order,
                    now,
                    now,
                    book.import_source,
                    book.import_payload_json,
                    book.extra_json,
                ),
            )
            book_id = int(cursor.lastrowid)
        created = self.get_book(book_id)
        if created is None:
            raise RuntimeError("创建书库记录失败。")
        return created

    def update_book(self, book: BookshelfBook) -> BookshelfBook:
        if book.id is None:
            raise ValueError("更新书库记录时缺少 id。")
        existing = self.get_book(book.id)
        if existing is None:
            raise ValueError("要更新的书库记录不存在。")
        updated_at = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE books
                SET custom_name = ?,
                    url = ?,
                    update_strategy = ?,
                    category = ?,
                    note = ?,
                    import_source = ?,
                    import_payload_json = ?,
                    extra_json = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    book.custom_name,
                    book.url,
                    book.update_strategy,
                    book.category,
                    book.note,
                    book.import_source,
                    book.import_payload_json,
                    book.extra_json,
                    updated_at,
                    book.id,
                ),
            )
        refreshed = self.get_book(book.id)
        if refreshed is None:
            raise RuntimeError("更新书库记录失败。")
        return refreshed

    def delete_book(self, book_id: int):
        book = self.get_book(book_id)
        if book is None:
            return
        with self._connect() as conn:
            conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            self._resequence_site(conn, book.site)

    def move_book(self, book_id: int, direction: str) -> bool:
        book = self.get_book(book_id)
        if book is None:
            return False
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, sort_order
                FROM books
                WHERE site = ?
                ORDER BY sort_order ASC, id ASC
                """,
                (book.site,),
            ).fetchall()
            ids = [int(row["id"]) for row in rows]
            try:
                index = ids.index(book_id)
            except ValueError:
                return False
            target_index = index - 1 if direction == "up" else index + 1
            if target_index < 0 or target_index >= len(ids):
                return False
            current_row = rows[index]
            target_row = rows[target_index]
            conn.execute(
                "UPDATE books SET sort_order = ?, updated_at = ? WHERE id = ?",
                (int(target_row["sort_order"]), self._now(), int(current_row["id"])),
            )
            conn.execute(
                "UPDATE books SET sort_order = ?, updated_at = ? WHERE id = ?",
                (int(current_row["sort_order"]), self._now(), int(target_row["id"])),
            )
        return True

    def _next_sort_order(self, conn: sqlite3.Connection, site: str) -> int:
        row = conn.execute(
            "SELECT MAX(sort_order) AS max_sort FROM books WHERE site = ?",
            (site,),
        ).fetchone()
        max_sort = row["max_sort"] if row and row["max_sort"] is not None else 0
        return int(max_sort) + 1

    def _resequence_site(self, conn: sqlite3.Connection, site: str):
        rows = conn.execute(
            """
            SELECT id
            FROM books
            WHERE site = ?
            ORDER BY sort_order ASC, id ASC
            """,
            (site,),
        ).fetchall()
        now = self._now()
        for index, row in enumerate(rows, start=1):
            conn.execute(
                "UPDATE books SET sort_order = ?, updated_at = ? WHERE id = ?",
                (index, now, int(row["id"])),
            )

    def _row_to_book(self, row: sqlite3.Row) -> BookshelfBook:
        return BookshelfBook(
            id=int(row["id"]),
            site=str(row["site"]),
            custom_name=str(row["custom_name"]),
            url=str(row["url"]),
            update_strategy=str(row["update_strategy"]),
            category=str(row["category"]),
            note=str(row["note"]),
            sort_order=int(row["sort_order"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            import_source=str(row["import_source"]),
            import_payload_json=str(row["import_payload_json"]),
            extra_json=str(row["extra_json"]),
        )

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()
