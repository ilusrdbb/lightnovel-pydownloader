from typing import Optional

from sqlmodel import Session, select

from models.cookie import Cookie
from utils import common


class CookieDatabase:

    def __init__(self, session: Session):
        self.session = session

    def update(self, data: Cookie):
        self.session.add(data)
        self.session.commit()
        self.session.refresh(data)

    def get_one(self, source: str) -> Optional[Cookie]:
        statement = select(Cookie).where(Cookie.source == source)
        return self.session.exec(statement).first()

    def insert_or_update(self, data: Cookie):
        cookie = self.get_one(data.source)
        if not cookie:
            self.update(data)
            return
        cookie.cookie = data.cookie
        cookie.token = data.token
        cookie.uid = data.uid
        self.update(cookie)
        common.copy(cookie, data)