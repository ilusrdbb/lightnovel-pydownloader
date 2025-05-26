from sqlalchemy import Column, String

from src.db import BaseDB


class Cookie(BaseDB):
    __tablename__ = 'cookie'

    id: str = Column(String, primary_key=True)
    # 站点
    source: str = Column(String, nullable=True)
    # 除轻国外使用cookie登录
    cookie: str = Column(String)
    # 轻国登录token 真白萌校验token
    token: str = Column(String)
    # 轻国用户id 真白萌ua
    uid: str = Column(String)

    def __str__(self):
        return (f"<Cookie(id={self.id}, source={self.source}, cookie={self.cookie}, "
                f"token={self.token}, uid={self.uid})>")