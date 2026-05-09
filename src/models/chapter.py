from typing import List, Dict, Optional

from sqlalchemy import String, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column

from src.db import BaseDB
from src.models.pic import Pic


class Chapter(BaseDB):
    __tablename__ = 'chapter'

    __table_args__ = (
        Index('idx_chapter', 'book_table_id'),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    # 关联数据库书籍表id
    book_table_id: Mapped[str] = mapped_column(String)
    # 章节id
    chapter_id: Mapped[str] = mapped_column(String)
    # 章节名称
    chapter_name: Mapped[Optional[str]] = mapped_column(String)
    # 顺序
    chapter_order: Mapped[Optional[int]] = mapped_column(Integer)
    # 爬取完整html章节内容
    content: Mapped[Optional[str]] = mapped_column(String)
    # 最后爬取时间 时间戳
    last_update_time: Mapped[Optional[int]] = mapped_column(Integer)
    # 是否购买失败 0否1是
    purchase_fail_flag: Mapped[Optional[int]] = mapped_column(Integer)

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
