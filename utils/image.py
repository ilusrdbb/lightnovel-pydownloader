import os
import pillow_avif
from typing import Optional

from PIL import Image
from aiohttp import ClientSession
from ebooklib import epub
from ebooklib.epub import EpubBook

from models.chapter import Chapter
from models.pic import Pic
from utils import common, config, log


async def download(pic: Pic, site: str, book_id: str, chapter_id: str, session: ClientSession):
    headers = {
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
    }
    file_url = pic.pic_url
    if site == "masiro" and file_url.startswith("/images"):
        file_url = config.read("url_config")[site]["pic"] % file_url
    if "lightnovel.fun" in file_url:
        headers["referer"] = "https://www.lightnovel.fun/"
    if "lightnovel.us" in file_url:
        file_url = file_url.replace("lightnovel.us", "lightnovel.fun")
        headers["referer"] = "https://www.lightnovel.fun/"
    if 'i.noire.cc:332' in file_url:
        file_url = file_url.replace("i.noire.cc:332", "i.noire.cc")
    file_name = common.filename_from_url(file_url)
    if file_name.endswith(".i"):
        file_name = file_name.replace(".i", ".avif")
    file_path = config.read("image_dir") + "/" + site + "/" + book_id + "/" + chapter_id + "/" + file_name
    # 创建文件夹
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    proxy = config.read('proxy_url') if config.read('proxy_url') else None
    timeout = config.read('time_out')
    try:
        res = await session.get(url=file_url, proxy=proxy, headers=headers, timeout=timeout)
        if not res.status == 200:
            raise Exception()
        image_data = await res.read()
        # 写入文件
        with open(file_path, 'wb') as f:
            f.write(image_data)
        # avif处理
        if file_name.endswith(".avif"):
            file_path = avif(file_path)
        pic.pic_path = file_path
    except Exception:
        log.info("%s 图片下载失败！" % pic.pic_url)
    return


async def cover(pic_url: str, site: str, book_id: str, session: ClientSession):
    headers = {
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
    }
    if site == "masiro" and pic_url.startswith("/images"):
        pic_url = config.read("url_config")[site]["pic"] % pic_url
    if "lightnovel.fun" in pic_url:
        headers["referer"] = "https://www.lightnovel.fun/"
    if "lightnovel.us" in pic_url:
        pic_url = pic_url.replace("lightnovel.us", "lightnovel.fun")
        headers["referer"] = "https://www.lightnovel.fun/"
    if 'i.noire.cc:332' in pic_url:
        pic_url = pic_url.replace("i.noire.cc:332", "i.noire.cc")
    file_name = "book_cover.jpg"
    file_path = config.read("image_dir") + "/" + site + "/" + book_id + "/" + file_name
    # 创建文件夹
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    proxy = config.read('proxy_url') if config.read('proxy_url') else None
    timeout = config.read('time_out')
    try:
        res = await session.get(url=pic_url, proxy=proxy, headers=headers, timeout=timeout)
        if not res.status == 200:
            raise Exception()
        image_data = await res.read()
        # 写入文件
        with open(file_path, 'wb') as f:
            f.write(image_data)
    except Exception:
        log.info("%s 封面下载失败！" % pic_url)
    return


def replace(chapter: Chapter, pics: Optional[Pic], epub_book: EpubBook):
    if not chapter.content or not pics:
        return
    content = chapter.content
    for pic in pics:
        try:
            image_data = open(pic.pic_path, "rb").read()
            image_name = common.filename_from_url(pic.pic_path)
            image_type = image_name.split('.')[-1]
            image = epub.EpubImage(uid=image_name, file_name='Image/' + image_name,
                                   media_type='image/' + image_type, content=image_data)
            epub_book.add_item(image)
            if pic.pic_id:
                content = content.replace(pic.pic_id, ("Image/" + image_name))
            else:
                content = content.replace(pic.pic_url, ("Image/" + image_name))
        except:
            continue
    chapter.content = content


def avif(in_path) -> str:
    try:
        avif_image = Image.open(in_path)
        png_image = avif_image.convert('RGB')
        out_path = os.path.splitext(in_path)[0] + '.png'
        png_image.save(out_path, 'PNG')
        avif_image.close()
        png_image.close()
    except:
        return in_path
    os.remove(in_path)
    return out_path
