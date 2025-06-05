import subprocess
import traceback

from src.models.book import Book
from src.utils.config import read_config
from src.utils.log import log


def push_calibre(book: Book):
    abs_path = read_config("push_calibre")["absolute_path"]
    container_name = read_config("push_calibre")["container_name"]
    library_path = read_config("push_calibre")["library_path"]
    if not container_name or not abs_path or not library_path:
        return
    full_path = abs_path + "/" + book.source + "/" + book.book_name + ".epub"
    log.info(f"{book.book_name} 开始推送calibre...")
    docker_command = ["docker", "exec", "-it", container_name]
    try:
        # calibre search
        calibre_search_command = f"calibredb search publisher:{book.source} 'title:\"{book.book_name}\"'"
        docker_search_command = docker_command + ["/bin/sh", "-c", calibre_search_command]
        log.debug(f"docker_search_command: {docker_search_command}")
        search_result = subprocess.run(docker_search_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        calibre_id = search_result.stdout
        if calibre_id and calibre_id.isdigit():
            # calibre remove
            calibre_remove_command = f"calibredb remove {str(calibre_id, encoding='utf-8')}"
            docker_remove_command = docker_command + ["/bin/sh", "-c", calibre_remove_command]
            log.debug(f"docker_remove_command: {docker_remove_command}")
            subprocess.run(docker_remove_command)
        # calibre add
        calibre_add_command = f"calibredb add \"{full_path}\" --with-library {library_path}"
        docker_add_command = docker_command + ["/bin/sh", "-c", calibre_add_command]
        log.debug(f"docker_add_command: {docker_add_command}")
        subprocess.run(docker_add_command)
        log.info(f"{book.book_name} 推送calibre成功！")
    except Exception as e:
        log.info(f"{book.book_name} 推送calibre失败！ {str(e)}")
        log.debug(traceback.print_exc())