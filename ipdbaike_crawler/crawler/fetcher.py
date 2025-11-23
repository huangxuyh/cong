import logging
from typing import Optional

import requests

from .config import HEADERS, JINA_PREFIX


def fetch_via_jina(url: str) -> Optional[str]:
    """
    通过 Jina Reader 拉取页面（markdown），适合被源站 403/反爬的场景。
    成功返回文本，失败返回 None。
    注意：Jina 返回的内容通常是 Markdown，后续解析需按 markdown 路径处理。
    """
    jina_url = JINA_PREFIX + url  # 拼出 Jina 代理地址
    try:
        resp = requests.get(jina_url, headers=HEADERS, timeout=30)  # 发起请求
        resp.raise_for_status()  # 非 2xx 抛异常
        logging.info("Jina fetch succeeded: %s", url)
        return resp.text  # 返回 markdown 文本
    except requests.RequestException as exc:
        logging.warning("Jina fetch failed: %s -> %s", url, exc)
        return None  # 失败返回 None


def fetch_direct(url: str) -> Optional[str]:
    """
    直接访问源站获取 HTML，适用于无需代理的站点。
    成功返回文本，失败返回 None。
    注意：会尝试自动设置 encoding 为 apparent_encoding。
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)  # 发起直连请求
        resp.raise_for_status()  # 非 2xx 抛异常
        resp.encoding = resp.apparent_encoding  # 根据内容推断编码
        logging.info("Direct fetch succeeded: %s", url)
        return resp.text  # 返回 HTML 文本
    except requests.RequestException as exc:
        logging.error("Direct fetch failed: %s -> %s", url, exc)
        return None  # 失败返回 None
