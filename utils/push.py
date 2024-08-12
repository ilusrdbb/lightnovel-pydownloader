from models.book import Book
from utils import config


def calibre(book: Book):
    if not config.read("push")["calibre"]:
        return
    # todo
    path = config.read("epub_dir") + "/" + book.source + "/" + book.book_name + ".epub"
