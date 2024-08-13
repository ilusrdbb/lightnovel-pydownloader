import os

import requests
from requests.auth import HTTPBasicAuth

from models.book import Book
from utils import config


def calibre(book: Book):
    calibre_url = config.read("push_calibre")["url"]
    username = config.read("push_calibre")["username"]
    password = config.read("push_calibre")["password"]
    if not calibre_url:
        return
    path = config.read("epub_dir") + "/" + book.source + "/" + book.book_name + ".epub"
    if not os.path.exists(path):
        return
    files = {
        'file': open(path, 'rb')
    }
    # 推送
    res = requests.post(calibre_url, files=files, auth=HTTPBasicAuth(username, password))
    if res.status_code == 200:
        print("%s 推送calibre成功！" % book.book_name)
    else:
        print("%s 推送calibre失败！" % book.book_name)
