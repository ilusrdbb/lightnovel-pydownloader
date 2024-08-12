import asyncio
import random

from aiohttp import ClientSession
from tenacity import retry, stop_after_attempt

from utils import config


@retry(stop=stop_after_attempt(3))
async def get(url: str, headers: dict, session: ClientSession) -> str:
    if config.read('sleep_time') > 0 and not 'masiro' in url:
        await asyncio.sleep(random.random() * config.read('sleep_time'))
    elif 'masiro.' in url:
        # 真白萌反爬严格，强制sleep
        await asyncio.sleep(10)
    proxy = config.read('proxy_url') if config.read('proxy_url') else None
    if 'masiro.' in url or '/v1' in url:
        proxy = None
    timeout = config.read('time_out')
    try:
        res = await session.get(url=url, headers=headers, proxy=proxy, timeout=timeout)
        if not res.status == 200:
            raise Exception()
        res_text = await res.text()
        return res_text
    except Exception:
        return None


@retry(stop=stop_after_attempt(3))
async def post_data(url: str, headers: dict, data: dict, session: ClientSession) -> dict:
    if config.read('sleep_time') > 0:
        await asyncio.sleep(random.random() * config.read('sleep_time'))
    proxy = config.read('proxy_url') if config.read('proxy_url') else None
    if 'masiro.' in url or '/v1' in url:
        proxy = None
    timeout = config.read('time_out')
    try:
        res = await session.post(url=url, headers=headers, proxy=proxy, data=data, timeout=timeout)
        if not res.status == 200:
            raise Exception()
        res_text = await res.text()
        return {
            "text": res_text,
            "headers": res.headers
        }
    except Exception:
        return None


@retry(stop=stop_after_attempt(3))
async def post_json(url: str, headers: dict, json: dict, session: ClientSession) -> str:
    if config.read('sleep_time') > 0:
        await asyncio.sleep(random.random() * config.read('sleep_time'))
    proxy = config.read('proxy_url') if config.read('proxy_url') else None
    timeout = config.read('time_out')
    if 'masiro.' in url or '/v1' in url:
        proxy = None
    if '/v1' in url:
        timeout = 120
    try:
        res = await session.post(url=url, headers=headers, proxy=proxy, json=json, timeout=timeout)
        if not res.status == 200:
            raise Exception()
        res_text = await res.text()
        return res_text
    except Exception:
        return None
