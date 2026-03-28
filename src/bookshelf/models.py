from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BookshelfBook:
    id: int | None = None
    site: str = "esj"
    custom_name: str = ""
    url: str = ""
    update_strategy: str = "only_new"
    category: str = ""
    note: str = ""
    sort_order: int = 0
    created_at: str = ""
    updated_at: str = ""
    import_source: str = ""
    import_payload_json: str = ""
    extra_json: str = ""
