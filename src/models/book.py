from typing import List, Dict, Any

from sqlalchemy import Column, String, Index

from src.db import BaseDB
from src.models.chapter import Chapter


class Book(BaseDB):
    __tablename__ = 'book'

    __table_args__ = (
        Index('idx_book', 'book_id', 'source'),
    )

    id: str =  Column(String, primary_key=True)
    # 书籍id
    book_id: str = Column(String, nullable=True)
    # 站点
    source: str = Column(String, nullable=True)
    # 书籍名称
    book_name: str = Column(String)
    # 书籍作者
    author: str = Column(String)
    # 书籍标签 英文逗号分隔
    tags: str = Column(String)
    # 书籍描述
    describe: str = Column(String)
    # 封面图片原始地址
    cover_url: str = Column(String)

    def __init__(self, **kwargs):
        # SQLAlchemy的默认初始化方法
        super().__init__(**kwargs)
        # esj缓存章节xpath列表
        self.chapter_xpaths: List = []
        # 真白萌缓存章节列表内容
        self.page_text: str = None
        # 轻国缓存章节列表内容
        self.chapter_datas: List[Dict[str, Any]] = []
        # 章节列表
        self.chapters: List[Chapter] = []

    def __str__(self):
        return (f"<Book(id={self.id}, book_id={self.book_id}, source={self.source}, book_name={self.book_name}, "
                f"author={self.author}, tags={self.tags}, cover_url={self.cover_url})>")


