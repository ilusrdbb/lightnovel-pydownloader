from typing import Optional

from sqlmodel import Session, select

from models.chapter import Chapter
from utils import common


class ChapterDatabase:

    def __init__(self, session: Session):
        self.session = session

    def update(self, data: Chapter):
        self.session.add(data)
        self.session.commit()
        self.session.refresh(data)

    def get_list(self, book_table_id: str) -> list[Chapter]:
        statement = select(Chapter).where(Chapter.book_table_id == book_table_id).order_by(Chapter.chapter_order)
        return self.session.exec(statement).all()

    def get_one(self, id: str) -> Optional[Chapter]:
        statement = select(Chapter).where(Chapter.id == id)
        return self.session.exec(statement).first()

    def insert_or_update(self, data: Chapter):
        chapter = self.get_one(data.id)
        if not chapter:
            self.update(data)
            return
        if data.chapter_name != chapter.chapter_name \
                or data.chapter_order != chapter.chapter_order \
                or data.content != chapter.content \
                or data.last_update_time != chapter.last_update_time \
                or data.purchase_fail_flag != chapter.purchase_fail_flag:
            chapter.chapter_name = data.chapter_name
            chapter.chapter_order = data.chapter_order
            chapter.content = data.content
            chapter.last_update_time = data.last_update_time
            chapter.purchase_fail_flag = data.purchase_fail_flag
            self.update(chapter)
        common.copy(chapter, data)

    def get_nopay_list(self) -> list[Chapter]:
        statement = select(Chapter).where(Chapter.purchase_fail_flag == 1)
        return self.session.exec(statement).all()

    def get_by_book(self, book_table_id: str) -> list[Chapter]:
        statement = select(Chapter).where(Chapter.book_table_id == book_table_id)
        return self.session.exec(statement).all()
