#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Standalone script to search WeChat public articles via Sogou, without importing project packages.
支持 “一次人工通过验证码 + 持久化 Cookie”：在浏览器里过一次验证码，把 Cookie 字符串放到文件（默认为 cookies.txt），脚本会加载并复用。

Usage:
    python wechat_search.py --query "新能源车" --limit 3 --pretty --cookie-file cookies.txt

Dependencies: requests, lxml
"""

import argparse
import json
import sys
import time
from typing import Dict, List, Any, Optional

import requests
from lxml import html
from urllib.parse import quote


HEADERS_COMMON = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36 Edg/137.0.0.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Connection": "keep-alive",
}


def load_cookie_header(path: str) -> str:
    """
    读取 Cookie 文件的首条非空行作为 Cookie 头。
    文件内容示例：SNUID=xxx; SUID=xxx; ABTEST=7; IPLOC=CN1100; SUV=...
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    return line
    except FileNotFoundError:
        pass
    return ""


def apply_cookies_to_session(session: requests.Session, cookie_header: str) -> None:
    """
    将 "k=v; k2=v2" 的 Cookie 头注入 session，覆盖搜狗与微信域名。
    - 保持与浏览器一致的 Cookie，降低反爬概率。
    """
    if not cookie_header:
        return
    parts = [p.strip() for p in cookie_header.split(";") if "=" in p]
    for part in parts:
        name, value = part.split("=", 1)
        for domain in ["weixin.sogou.com", "mp.weixin.qq.com"]:
            session.cookies.set(name.strip(), value.strip(), domain=domain)


def sogou_weixin_search(query: str, session: requests.Session) -> List[Dict[str, str]]:
    """
    在搜狗检索文章，返回标题/链接/时间。
    - 结果链接通常为搜狗跳转页，需要后续解析 real_url。
    """
    headers = {
        **HEADERS_COMMON,
        "Referer": f"https://weixin.sogou.com/weixin?query={quote(query)}",
    }
    params = {
        "type": "2",
        "s_from": "input",
        "query": query,
        "ie": "utf8",
        "_sug_": "n",
        "_sug_type_": "",
    }
    response = session.get("https://weixin.sogou.com/weixin", params=params, headers=headers, timeout=15)
    response.raise_for_status()

    tree = html.fromstring(response.text)
    results = []
    elements = tree.xpath("//a[contains(@id, 'sogou_vr_11002601_title_')]")
    publish_time = tree.xpath(
        "//li[contains(@id, 'sogou_vr_11002601_box_')]/div[@class='txt-box']/div[@class='s-p']/span[@class='s2']"
    )

    for element, time_elem in zip(elements, publish_time):
        title = element.text_content().strip()
        link = element.get("href")
        if link and not link.startswith("http"):
            link = "https://weixin.sogou.com" + link
        results.append(
            {
                "title": title,
                "link": link,
                "publish_time": time_elem.text_content().strip(),
            }
        )
    return results


def get_real_url(sogou_url: str, session: requests.Session) -> str:
    """
    解析搜狗跳转页，获取真实 mp.weixin.qq.com 链接（优先 302，其次 JS 拼接）。
    - 若返回 antispider，需要刷新 Cookie 或人工验证。
    """
    # First try to read the redirect target (often 302 Location on Sogou jump page)
    resp = session.get(sogou_url, headers=HEADERS_COMMON, timeout=15, allow_redirects=False)
    if resp.is_redirect or resp.is_permanent_redirect:
        loc = resp.headers.get("Location", "")
        if loc:
            loc = loc.replace("@", "").replace(" ", "")
            if loc.startswith("//"):
                loc = "https:" + loc
            elif not loc.startswith("http"):
                loc = "https://" + loc.lstrip("/")
            return loc

    # If not redirected, parse the JS concat on the page
    resp = session.get(sogou_url, headers=HEADERS_COMMON, timeout=15)
    resp.raise_for_status()

    import re

    parts = re.findall(r"url \\+= '([^']+)'", resp.text)
    if not parts:
        return ""
    joined = "".join(parts).replace("@", "")

    if joined.startswith("http"):
        return joined
    if joined.startswith("//"):
        return "https:" + joined
    return "https://" + joined.lstrip("/")


def get_article_content(real_url: str, referer: str, session: requests.Session) -> str:
    """
    拉取微信文章正文，提取 #js_content 文本。
    """
    headers = {
        **HEADERS_COMMON,
        "Referer": referer,
        "Upgrade-Insecure-Requests": "1",
    }
    resp = session.get(real_url, headers=headers, timeout=15)
    resp.raise_for_status()
    tree = html.fromstring(resp.text)
    content_elements = tree.xpath("//div[@id='js_content']//text()")
    cleaned_content = [text.strip() for text in content_elements if text.strip()]
    return "\n".join(cleaned_content)


def get_wechat_article(query: str, number: int, cookie_header: str) -> List[Dict[str, Any]]:
    """
    搜索并抓取文章正文，使用持久化 Cookie 提升成功率。
    """
    start_time = time.time()
    session = requests.Session()
    session.headers.update(HEADERS_COMMON)
    apply_cookies_to_session(session, cookie_header)

    results = sogou_weixin_search(query, session=session)
    if not results:
        return []
    articles = []
    for entry in results[:number]:
        sogou_link = entry["link"]
        real_url = get_real_url(sogou_link, session=session)
        content = get_article_content(real_url, referer=sogou_link, session=session) if real_url else ""
        articles.append(
            {
                "title": entry["title"],
                "publish_time": entry["publish_time"],
                "real_url": real_url,
                "content": content,
            }
        )
    duration = time.time() - start_time
    print(f"Fetched {len(articles)} articles for '{query}' in {duration:.2f}s")
    return articles


def main() -> None:
    parser = argparse.ArgumentParser(description="Search WeChat public articles (via Sogou).")
    parser.add_argument("-q", "--query", required=True, help="Keyword to search")
    parser.add_argument("-n", "--limit", type=int, default=5, help="Number of articles to fetch (default: 5)")
    parser.add_argument("--cookie-file", default="cookies.txt", help="Cookie 文件路径（默认 cookies.txt）")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args()

    cookie_header = load_cookie_header(args.cookie_file)
    if not cookie_header:
        print(f"提示：未找到 Cookie，可能仍会被反爬。请将浏览器里通过验证码后的 Cookie 放到 {args.cookie_file}", file=sys.stderr)

    try:
        results = get_wechat_article(query=args.query, number=args.limit, cookie_header=cookie_header)
    except Exception as exc:  # noqa: BLE001
        print(f"Search failed: {exc}", file=sys.stderr)
        sys.exit(1)

    indent = 2 if args.pretty else None
    print(json.dumps(results, indent=indent, ensure_ascii=False))


if __name__ == "__main__":
    main()
