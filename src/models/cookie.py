from typing import Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from src.db import BaseDB


class Cookie(BaseDB):
    __tablename__ = 'cookie'

    id: Mapped[str] = mapped_column(String, primary_key=True)
    # 站点
    source: Mapped[Optional[str]] = mapped_column(String, default='')
    # 除轻国外使用cookie登录
    cookie: Mapped[str] = mapped_column(String)
    # 轻国登录token 真白萌校验token
    token: Mapped[str] = mapped_column(String)
    # 轻国用户id 真白萌ua
    uid: Mapped[str] = mapped_column(String)

    def __str__(self):
        return (f"<Cookie(id={self.id}, source={self.source}, cookie={self.cookie}, "
                f"token={self.token}, uid={self.uid})>")
