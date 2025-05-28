from typing import List, Dict

from sqlalchemy import Column, String, Integer, Index

from src.db import BaseDB
from src.models.pic import Pic


class Chapter(BaseDB):
    __tablename__ = 'chapter'

    __table_args__ = (
        Index('idx_chapter', 'book_table_id'),
    )

    id: str = Column(String, primary_key=True)
    # 关联数据库书籍表id
    book_table_id: str = Column(String, nullable=True)
    # 章节id
    chapter_id: str = Column(String, nullable=True)
    # 章节名称
    chapter_name: str = Column(String)
    # 顺序
    chapter_order: int = Column(Integer, nullable=True)
    # 爬取完整html章节内容
    content: str = Column(String)
    # 最后爬取时间 时间戳
    last_update_time: int = Column(Integer)
    # 是否购买失败 0否1是
    purchase_fail_flag: int = Column(Integer)

    def __init__(self, **kwargs):
        # SQLAlchemy的默认初始化方法
        super().__init__(**kwargs)
        # 书籍id 用于拼接章节路径和url地址
        self.book_id: str = None
        # 花费金币
        self.cost: int = 0
        # 图片列表
        self.pics: List[Pic] = []
        # 轻国缓存图片信息
        self.pic_datas: List[Dict[str, str]] = []

    def __str__(self):
        return (f"<Chapter(id={self.id}, book_table_id={self.book_table_id}, chapter_id={self.chapter_id}, "
                f"chapter_name={self.chapter_name}, chapter_order={self.chapter_order}, last_update_time={self.last_update_time})>")
