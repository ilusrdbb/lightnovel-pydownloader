import yaml
from lxml import html

config_data = {}


def init_config():
    with open('config.yaml', 'r', encoding='utf-8') as f:
        global config_data
        config_data = yaml.safe_load(f)


def read(key):
    return config_data.get(key)


def get_xpath(text: str, site: str, name: str) -> list:
    page_body = html.fromstring(text)
    return page_body.xpath(read("xpath_config")[site][name])


def get_html(text: str, site: str, name: str) -> str:
    if not text:
        return None
    page_body = html.fromstring(text)
    xpaths = page_body.xpath(read("xpath_config")[site][name])
    if not xpaths:
        return None
    html_str = []
    for xpath in xpaths:
        html_str.append(html.tostring(xpath, pretty_print=True, encoding="unicode"))
    return "\n".join(html_str)
