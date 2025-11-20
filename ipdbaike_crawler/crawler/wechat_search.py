#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Standalone script to search WeChat public articles via Sogou, without importing project packages.

Usage:
    python wechat_search.py --query "新能源车" --limit 3 --pretty

Dependencies: requests, lxml
"""

import argparse
import json
import sys
import time
from typing import Dict, List, Any

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


def sogou_weixin_search(query: str) -> List[Dict[str, str]]:
    """
    Search WeChat articles on Sogou and return basic metadata.
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
    response = requests.get("https://weixin.sogou.com/weixin", params=params, headers=headers, timeout=15)
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


def get_real_url(sogou_url: str) -> str:
    """
    Extract the real mp.weixin.qq.com article URL from the Sogou jump page.
    """
    headers = {
        **HEADERS_COMMON,
        "Cookie": "ABTEST=7; SUID=0A5BF4788E52A20B; IPLOC=CN1100; SUV=006817F578F45BFE",
    }
    resp = requests.get(sogou_url, headers=headers, timeout=15)
    resp.raise_for_status()

    script_content = resp.text
    start_index = script_content.find("url += '") + len("url += '")
    url_parts = []
    while True:
        part_start = script_content.find("url += '", start_index)
        if part_start == -1:
            break
        part_end = script_content.find("'", part_start + len("url += '"))
        part = script_content[part_start + len("url += '") : part_end]
        url_parts.append(part)
        start_index = part_end + 1

    full_url = "".join(url_parts).replace("@", "")
    return "https://mp." + full_url


def get_article_content(real_url: str, referer: str) -> str:
    """
    Fetch article HTML and extract readable text.
    """
    headers = {
        **HEADERS_COMMON,
        "Referer": referer,
        "Upgrade-Insecure-Requests": "1",
    }
    resp = requests.get(real_url, headers=headers, timeout=15)
    resp.raise_for_status()
    tree = html.fromstring(resp.text)
    content_elements = tree.xpath("//div[@id='js_content']//text()")
    cleaned_content = [text.strip() for text in content_elements if text.strip()]
    return "\n".join(cleaned_content)


def get_wechat_article(query: str, number: int = 10) -> List[Dict[str, Any]]:
    """
    Search and fetch full articles (title, time, real_url, content).
    """
    start_time = time.time()
    results = sogou_weixin_search(query)
    if not results:
        return []
    articles = []
    for entry in results[:number]:
        sogou_link = entry["link"]
        real_url = get_real_url(sogou_link)
        content = get_article_content(real_url, referer=sogou_link) if real_url else ""
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
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args()

    try:
        results = get_wechat_article(query=args.query, number=args.limit)
    except Exception as exc:  # noqa: BLE001
        print(f"Search failed: {exc}", file=sys.stderr)
        sys.exit(1)

    indent = 2 if args.pretty else None
    print(json.dumps(results, indent=indent, ensure_ascii=False))


if __name__ == "__main__":
    main()
