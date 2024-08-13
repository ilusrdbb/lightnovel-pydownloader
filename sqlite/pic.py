from typing import Optional

from sqlalchemy.sql.operators import isnot
from sqlmodel import Session, select, update

from models.pic import Pic
from utils import common


class PicDatabase:

    def __init__(self, session: Session):
        self.session = session

    def update(self, data: Pic):
        self.session.add(data)
        self.session.commit()
        self.session.refresh(data)

    def get_list(self, chapter_table_id: str) -> list[Pic]:
        statement = select(Pic).where(Pic.chapter_table_id == chapter_table_id)
        return self.session.exec(statement).all()

    def get_nonnull_list(self, chapter_table_id: str) -> list[Pic]:
        statement = select(Pic).where(Pic.chapter_table_id == chapter_table_id, isnot(Pic.pic_path, None))
        return self.session.exec(statement).all()

    def get_null_list(self) -> list[Pic]:
        statement = select(Pic).where(Pic.pic_path.is_(None))
        return self.session.exec(statement).all()

    def get_one(self, id: str) -> Optional[Pic]:
        statement = select(Pic).where(Pic.id == id)
        return self.session.exec(statement).first()

    def insert_or_update(self, data: Pic):
        pic = self.get_one(data.id)
        if not pic:
            self.update(data)
            return
        if data.pic_path != pic.pic_path :
            pic.pic_path = data.pic_path
            self.update(pic)
        common.copy(pic, data)

    def clear(self):
        statement = update(Pic).values(pic_path=None)
        # 执行更新操作
        self.session.execute(statement)
        self.session.commit()
