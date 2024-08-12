from sqlmodel import Field, SQLModel


class Book(SQLModel, table=True):
    id: str = Field(default=None, primary_key=True, index=True)
    book_id: str = Field(alias="book_id", title="爬取网站的书籍id")
    source: str = Field(alias="source", title="爬取来源")
    book_name: str = Field(alias="book_name", title="书籍名称")
    author: str = Field(alias="author", title="作者")
    tags: str = Field(alias="tags", title="标签英文逗号分隔")
    describe: str = Field(alias="describe", title="书籍描述")
    cover_url: str = Field(alias="cover_url", title="封面地址")


