import subprocess

from models.book import Book
from utils import config, log


def calibre(book: Book):
    abs_path = config.read("push_calibre")["absolute_path"]
    container_id = config.read("push_calibre")["container_id"]
    library_path = config.read("push_calibre")["library_path"]
    if not container_id or not abs_path or not library_path:
        return
    full_path = abs_path + "/" + book.source + "/" + book.book_name + ".epub"
    # calibre推送api
    calibre_command = "calibredb add " + full_path + " --with-library " + library_path
    docker_command = ["docker", "exec", "-d", container_id] + ["/bin/sh", "-c", calibre_command]
    log.info("%s 开始推送calibre..." % book.book_name)
    try:
        # 执行docker命令
        subprocess.run(docker_command, capture_output=True, text=True)
        log.info("%s 推送calibre成功！" % book.book_name)
    except:
        log.info("%s 推送calibre失败！" % book.book_name)