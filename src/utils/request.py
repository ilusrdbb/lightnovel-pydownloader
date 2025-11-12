import asyncio
import os
import random
import traceback
from typing import Dict

from aiohttp import ClientSession
from tenacity import retry, stop_after_attempt, retry_if_exception_type

from src.utils import common
from src.utils.config import read_config
from src.utils.log import log

# 定义哪些异常应该触发重试
RETRYABLE_EXCEPTIONS = (
    asyncio.TimeoutError
)

@retry(
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS)
)
async def get(url: str, headers: Dict, session: ClientSession) -> str:
    await sleep(url)
    proxy = read_config("proxy_url") if read_config("proxy_url") and "/v1" not in url else None
    if read_config("domain")["yuri"] in url:
        # 百合会开启代理签到会报错
        proxy = None
    timeout = read_config("time_out")
    try:
        res = await session.get(url=url, headers=headers, proxy=proxy, timeout=timeout)
        if not res.status == 200:
            log.info(f"{url}请求失败 {res.status}")
            return None
        text = await res.text("utf-8", "ignore")
        return text
    except RETRYABLE_EXCEPTIONS as e:
        log.info(f"{url}请求超时，重试...")
        raise e


@retry(
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS)
)
async def post_data(url: str, headers: Dict, data: Dict, session: ClientSession) -> dict:
    await sleep(url)
    proxy = read_config("proxy_url") if read_config("proxy_url") and "/v1" not in url else None
    timeout = read_config("time_out")
    try:
        res = await session.post(url=url, headers=headers, proxy=proxy, data=data, timeout=timeout)
        if not res.status == 200:
            log.info(f"{url}请求失败 {res.status}")
            return None
        text = await res.text()
        return {
            "text": text,
            "headers": res.headers
        }
    except RETRYABLE_EXCEPTIONS as e:
        log.info(f"{url}请求超时，重试...")
        raise e


@retry(
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS)
)
async def post_json(url: str, headers: Dict, json: Dict, session: ClientSession) -> str:
    await sleep(url)
    proxy = read_config("proxy_url") if read_config("proxy_url") and "/v1" not in url else None
    timeout = 120 if "/v1" in url else read_config("time_out")
    try:
        res = await session.post(url=url, headers=headers, proxy=proxy, json=json, timeout=timeout)
        if not res.status == 200:
            log.info(f"{url}请求失败 {res.status}")
            return None
        text = await res.text()
        return text
    except RETRYABLE_EXCEPTIONS as e:
        log.info(f"{url}请求超时，重试...")
        raise e

async def sleep(url: str):
    if 'masiro.' in url:
        await asyncio.sleep(6)
    elif read_config("sleep_time") > 0:
        await asyncio.sleep(random.random() * read_config("sleep_time"))

async def download_pic(url: str, headers: Dict, path: str, session: ClientSession, json: Dict=None) -> str:
    if 'i.noire.cc:332' in url:
        url = url.replace("i.noire.cc:332", "i.noire.cc")
    file_name = common.filename_from_url(url)
    if file_name.endswith(".i"):
        file_name = file_name.replace(".i", ".avif")
    if "." not in file_name:
        file_name = file_name + ".png"
    proxy = read_config("proxy_url") if read_config("proxy_url") and "/v1" not in url else None
    timeout = read_config("time_out")
    try:
        res = await session.get(url=url, proxy=proxy, headers=headers, json=json, timeout=timeout)
        if not res.status == 200:
            raise Exception(res.status)
        image_data = await res.read()
        # 写入图片
        full_path = f"{path}/{file_name}"
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'wb') as f:
            f.write(image_data)
            log.debug(f"{url}图片下载成功 保存路径{full_path}")
        # 轻国avif处理
        if file_name.endswith(".avif"):
            return common.handle_avif(path)
        return full_path
    except Exception as e:
        log.info(f"{url}图片下载失败 {str(e)}")
        log.debug(traceback.print_exc())
        return None


async def download_file(url: str, headers: Dict, path: str, session: ClientSession):
    proxy = read_config("proxy_url") if read_config("proxy_url") and "/v1" not in url else None
    timeout = read_config("time_out")
    try:
        res = await session.get(url=url, proxy=proxy, headers=headers, timeout=timeout)
        if not res.status == 200:
            raise Exception(res.status)
        file_data = await res.read()
        # 写入
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            f.write(file_data)
            log.debug(f"{url}文件下载成功 保存路径{path}")
    except Exception as e:
        log.info(f"{url}文件下载失败 {str(e)}")
        log.debug(traceback.print_exc())

