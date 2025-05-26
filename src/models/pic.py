from typing import Dict

from sqlalchemy import Column, String, Index

from src.db import BaseDB


class Pic(BaseDB):
    __tablename__ = 'pic'

    __table_args__ = (
        Index('idx_pic', 'chapter_table_id'),
        Index('idx_url', 'pic_url'),
    )

    id: str = Column(String, primary_key=True)
    # 关联数据库章节表id
    chapter_table_id: str = Column(String, nullable=True)
    # 图片原始地址
    pic_url: str = Column(String, nullable=True)
    # 爬取后图片存放相对路径
    pic_path: str = Column(String)
    # 图片id 仅轻国需要
    pic_id: str = Column(String)

    def __str__(self):
        return (f"<Pic(id={self.id}, chapter_table_id={self.chapter_table_id}, pic_url={self.pic_url}, "
                f"pic_path={self.pic_path}, pic_id={self.pic_id})>")