import subprocess
import traceback

from src.core.constants import SUBPROCESS_TIMEOUT
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
    docker_command = ["docker", "exec", container_name]
    try:
        # calibre search
        search_query = f'publisher:{book.source} title:"{book.book_name}"'
        docker_search_command = docker_command + ["calibredb", "search", search_query]
        log.debug(f"docker_search_command: {docker_search_command}")
        search_result = subprocess.run(
            docker_search_command,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=SUBPROCESS_TIMEOUT
        )
        calibre_id = search_result.stdout
        if calibre_id and calibre_id.strip().isdigit():
            # calibre remove
            docker_remove_command = docker_command + ["calibredb", "remove", calibre_id.decode("utf-8").strip()]
            log.debug(f"docker_remove_command: {docker_remove_command}")
            subprocess.run(docker_remove_command, timeout=SUBPROCESS_TIMEOUT)
        # calibre add
        docker_add_command = docker_command + ["calibredb", "add", full_path, "--with-library", library_path]
        log.debug(f"docker_add_command: {docker_add_command}")
        subprocess.run(docker_add_command, timeout=SUBPROCESS_TIMEOUT)
        log.info(f"{book.book_name} 推送calibre成功！")
    except subprocess.TimeoutExpired:
        log.info(f"{book.book_name} 推送calibre超时！")
    except Exception as e:
        log.info(f"{book.book_name} 推送calibre失败！ {str(e)}")
        log.debug(traceback.format_exc())
