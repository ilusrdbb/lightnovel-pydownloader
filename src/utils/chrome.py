import asyncio
import platform
import re
import time
from typing import Optional, Dict

from DrissionPage import Chromium, ChromiumOptions

from src.utils.config import read_config
from src.utils.log import log

_MAX_RETRIES = 3
_SLEEP_TIME = 5
_MAX_WAIT_TIME = 240
_TRY_CF_TIME = 240

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

def _build_chrome_options():
    co = ChromiumOptions()
    co.auto_port()
    co.headless(True)
    # Linux无头环境需要额外参数
    if platform.system() == 'Linux':
        co.set_argument('--no-sandbox')
    return co

def _bypass_cf_sync(url: str) -> Optional[Dict[str, str]]:
    co = _build_chrome_options()
    browser = None
    try:
        try:
            browser = Chromium(co)
        except Exception as e:
            log.info(f"Chrome启动失败: {e}")
            log.info("未找到系统安装的 Chrome 浏览器，请先安装 Chrome。")
            return None
        tab = browser.latest_tab
        log.info("等待页面加载...")
        tab.get(url)
        start = time.time()
        clicked = False
        # 改为自旋而不是循环重试 防止卡死
        while time.time() - start < _MAX_WAIT_TIME:
            time.sleep(_SLEEP_TIME)
            # 前40秒尝试点击验证按钮 之后只等待自动放行
            if not clicked and time.time() - start <= _TRY_CF_TIME:
                button = _locate_cf_button(tab)
                if button:
                    log.info("找到验证按钮，点击中...")
                    button.click()
                    clicked = True
            cf_clearance = None
            for cookie in tab.cookies():
                if cookie.get('name') == 'cf_clearance':
                    cf_clearance = cookie.get('value')
                    break
            if cf_clearance:
                log.info("破cf盾成功！")
                user_agent = tab.run_js('return navigator.userAgent;')
                return {
                    "user_agent": user_agent,
                    "cf_clearance": cf_clearance,
                }
        log.info("未找到cf_clearance")
        return None
    finally:
        if browser:
            browser.quit()

def _waf_page_ready(tab, ready_keywords):
    # 判断是否出现真实页面
    try:
        title = (tab.title or "").strip()
        text_len = tab.run_js("return document.body ? document.body.innerText.length : 0;")
        if not title or text_len < 50:
            # NoX挑战页通常无标题、body只有脚本，innerText为空
            return False
        if ready_keywords is None:
            return True
        return any(k in title for k in ready_keywords)
    except Exception:
        return False

async def bypass_waf(url: str) -> Optional[Dict[str, str]]:
    log.info("开始绕过WAF...")
    try:
        result = await asyncio.to_thread(_bypass_waf_sync, url, ("百合会", "Discuz"))
        return result
    except Exception as e:
        log.info(f"绕过WAF失败: {e}")
        return None

def _get_discuz_hash(tab):
    # discuz论坛formhash和loginhash顺便从页面里拿了
    try:
        formhash = tab.run_js(
            "return (document.querySelector('input[name=\"formhash\"]')||{}).value || null;"
        )
        action = tab.run_js(
            "return (document.querySelector('form[name=\"login\"]')"
            " || document.querySelector('form[id^=\"loginform_\"]') || {}).getAttribute('action') || '';"
        ) or ""
        m = re.search(r"loginhash=([A-Za-z0-9]+)", str(action))
        return {"formhash": formhash, "loginhash": m.group(1) if m else None}
    except Exception as e:
        log.info(f"获取hash失败: {e}")
        return {}

def _bypass_waf_sync(url: str, ready_keywords: Optional[tuple] = None) -> Optional[Dict[str, str]]:
    co = _build_chrome_options()
    browser = None
    try:
        try:
            browser = Chromium(co)
        except Exception as e:
            log.info(f"Chrome启动失败: {e}")
            log.info("未找到系统安装的 Chrome 浏览器，请先安装 Chrome。")
            return None
        tab = browser.latest_tab
        log.info("等待页面加载...")
        for i in range(_MAX_RETRIES):
            try:
                tab.get(url)
            except Exception as e:
                log.debug(f"第{i + 1}次访问 {url} 异常: {e}")
            # 等一会 完成页面加载
            time.sleep(_SLEEP_TIME)
            if _waf_page_ready(tab, ready_keywords):
                log.info("页面已就绪")
                break
            log.info(f"第{i + 1}次尝试: 页面未就绪，重试...")
        # 等待页面跳转
        time.sleep(_SLEEP_TIME)
        if not _waf_page_ready(tab, ready_keywords):
            log.info("多次尝试后页面仍未就绪，绕过WAF失败")
            return None
        # 提取discuz hash
        discuz_hash = _get_discuz_hash(tab)
        # 提取waf cookie和user_agent
        log.info("开始获取waf cookie...")
        user_agent = tab.run_js('return navigator.userAgent;')
        cookie_list = tab.cookies()
        cookie_dict = {
            c.get('name'): c.get('value')
            for c in cookie_list if c.get('name') and c.get('value') is not None
        }
        log.info("绕过WAF成功！")
        result = {
            "user_agent": user_agent,
            "cookie": "; ".join(f"{k}={v}" for k, v in cookie_dict.items())
        }
        if discuz_hash.get("formhash"):
            result["formhash"] = discuz_hash.get("formhash")
        if discuz_hash.get("loginhash"):
            result["loginhash"] = discuz_hash.get("loginhash")
        return result
    finally:
        if browser:
            browser.quit()
