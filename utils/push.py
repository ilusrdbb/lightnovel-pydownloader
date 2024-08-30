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
    log.info("%s 开始推送calibre..." % book.book_name)
    docker_command = ["docker", "exec", "-it", container_id]
    try:
        # calibre search
        calibre_search_command = "calibredb search publisher:" + book.source + \
                                 " 'title:\"" + book.book_name + "\"'"
        docker_search_command = docker_command + ["/bin/sh", "-c", calibre_search_command]
        search_result = subprocess.run(docker_search_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        calibre_id = search_result.stdout
        if calibre_id and calibre_id.isdigit():
            # calibre remove
            calibre_remove_command = "calibredb remove " + calibre_id
            docker_remove_command = docker_command + ["/bin/sh", "-c", calibre_remove_command]
            subprocess.run(docker_remove_command)
        # calibre add
        calibre_add_command = "calibredb add \"" + full_path + "\" --with-library " + library_path
        docker_add_command = docker_command + ["/bin/sh", "-c", calibre_add_command]
        subprocess.run(docker_add_command)
        log.info("%s 推送calibre成功！" % book.book_name)
    except:
        log.info("%s 推送calibre失败！" % book.book_name)