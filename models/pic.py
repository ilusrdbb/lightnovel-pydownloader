from sqlmodel import SQLModel, Field


class Pic(SQLModel, table=True):
    id: str = Field(default=None, primary_key=True, index=True)
    chapter_table_id: str = Field(alias="chapter_table_id", title="关联数据库章节id")
    pic_url: str = Field(alias="pic_url", title="图片地址")
    pic_path: str = Field(alias="pic_path", title="图片存放路径")
    pic_id: str = Field(alias="pic_id", title="图片id，仅轻国需要")