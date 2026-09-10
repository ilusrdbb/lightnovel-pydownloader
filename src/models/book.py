from typing import Any

from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column

from src.db import BaseDB
from src.models.chapter import Chapter


class Book(BaseDB):
    __tablename__ = 'book'

    __table_args__ = (
        Index('idx_book', 'book_id', 'source'),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    # 书籍id
    book_id: Mapped[str] = mapped_column(String)
    # 站点
    source: Mapped[str] = mapped_column(String)
    # 书籍名称
    book_name: Mapped[str | None] = mapped_column(String)
    # 书籍作者
    author: Mapped[str | None] = mapped_column(String)
    # 书籍标签 英文逗号分隔
    tags: Mapped[str | None] = mapped_column(String)
    # 书籍描述
    describe: Mapped[str | None] = mapped_column(String)
    # 封面图片原始地址
    cover_url: Mapped[str | None] = mapped_column(String)

    def __init__(self, **kwargs):
        # SQLAlchemy的默认初始化方法
        super().__init__(**kwargs)
        # esj缓存章节xpath列表
        self.chapter_xpaths: list = []
        # 真白萌缓存章节列表内容
        self.page_text: str | None = None
        # 轻国缓存章节列表内容
        self.chapter_datas: list[dict[str, Any]] = []
        # 新版轻国缓存卷列表内容
        self.volume_datas: list[dict[str, Any]] = []
        # 章节列表
        self.chapters: list[Chapter] = []

    def __str__(self) -> str:
        return (f"<Book(id={self.id}, book_id={self.book_id}, source={self.source}, book_name={self.book_name}, "
                f"author={self.author}, tags={self.tags}, cover_url={self.cover_url})>")
