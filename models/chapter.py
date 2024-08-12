from sqlmodel import SQLModel, Field


class Chapter(SQLModel, table=True):
    id: str = Field(default=None, primary_key=True, index=True)
    book_table_id: str = Field(alias="book_table_id", title="关联数据库书籍id")
    chapter_id: str = Field(alias="chapter_id", title="爬取网站的章节id")
    chapter_name: str = Field(alias="chapter_name", title="章节名称")
    chapter_order: int = Field(alias="chapter_order", title="顺序")
    content: str = Field(alias="content", title="完整html内容")
    last_update_time: int = Field(alias="last_update_time", title="最后爬取时间")
    purchase_fail_flag: int = Field(alias="purchase_fail_flag", title="购买失败标识0否1是")
