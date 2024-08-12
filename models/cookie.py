from sqlmodel import SQLModel, Field


class Cookie(SQLModel, table=True):
    id: str = Field(default=None, primary_key=True, index=True)
    source: str = Field(alias="source", title="source")
    cookie: str = Field(alias="cookie", title="cookie")
    token: str = Field(alias="token", title="token")
    uid: str = Field(alias="uid", title="uid")
