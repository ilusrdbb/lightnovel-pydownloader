import asyncio
import platform
import time
from typing import Optional, Dict

from DrissionPage import Chromium, ChromiumOptions

from src.utils.log import log

_MAX_RETRIES = 5
_SLEEP_TIME = 7

def _locate_cf_button(tab):
    # 尝试通过turnstile hidden input定位
    try:
        eles = tab.eles("tag:input")
        for ele in eles:
            attrs = ele.attrs
            if ("name" in attrs and "type" in attrs
                    and "turnstile" in attrs["name"] and attrs["type"] == "hidden"):
                button = ele.parent().shadow_root.child()("tag:body").shadow_root("tag:input")
                if button:
                    return button
    except Exception:
        pass
    # 尝试递归查找shadow root中的iframe
    try:
        body = tab.ele("tag:body")
        iframe = _search_shadow_root_iframe(body)
        if iframe:
            button = _search_shadow_root_input(iframe("tag:body"))
            if button:
                return button
    except Exception:
        pass
    return None

def _search_shadow_root_iframe(ele):
    # 递归查找包含iframe的shadow root
    try:
        if ele.shadow_root:
            child = ele.shadow_root.child()
            if child and child.tag == "iframe":
                return child
        for child in ele.children():
            result = _search_shadow_root_iframe(child)
            if result:
                return result
    except Exception:
        pass
    return None

def _search_shadow_root_input(ele):
    # 递归查找shadow root中的input元素
    try:
        if ele.shadow_root:
            inp = ele.shadow_root.ele("tag:input")
            if inp:
                return inp
        for child in ele.children():
            result = _search_shadow_root_input(child)
            if result:
                return result
    except Exception:
        pass
    return None

async def bypass_cf(url: str) -> Optional[Dict[str, str]]:
    log.info("开始破cf盾...")
    try:
        result = await asyncio.to_thread(_bypass_cf_sync, url)
        return result
    except Exception as e:
        log.info(f"破cf盾失败: {e}")
        return None

def _bypass_cf_sync(url: str) -> Optional[Dict[str, str]]:
    co = ChromiumOptions()
    co.auto_port()
    # Linux无头环境需要额外参数
    if platform.system() == 'Linux':
        co.set_argument('--no-sandbox')
    browser = None
    try:
        try:
            browser = Chromium(co)
        except Exception as e:
            log.debug(f"Chrome启动失败: {e}")
            log.info("未找到系统安装的 Chrome 浏览器，请先安装 Chrome。")
            return None
        tab = browser.latest_tab
        tab.get(url)
        log.info("等待页面加载...")
        for i in range(_MAX_RETRIES):
            time.sleep(_SLEEP_TIME)
            # 尝试找按钮并点击
            button = _locate_cf_button(tab)
            if button:
                log.info(f"第{i + 1}次尝试: 找到验证按钮，点击中...")
                button.click()
                log.info("点击成功，等待页面跳转...")
                break
            else:
                log.info(f"第{i + 1}次尝试: 未找到验证按钮，重试...")
        # 等待页面跳转
        time.sleep(_SLEEP_TIME)
        # 提取cf_clearance cookie和user_agent
        log.info("开始获取cf_clearance...")
        user_agent = tab.run_js('return navigator.userAgent;')
        cf_clearance = None
        for cookie in tab.cookies():
            if cookie.get('name') == 'cf_clearance':
                cf_clearance = cookie.get('value')
                break
        if cf_clearance:
            log.info("破cf盾成功！")
            return {
                "user_agent": user_agent,
                "cf_clearance": cf_clearance,
            }
        log.info("未找到cf_clearance")
        return None
    finally:
        if browser:
            browser.quit()
