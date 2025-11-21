"""
Use Playwright to fetch WeChat articles via Sogou with a real browser.

Usage (run from repo root or crawler/ dir):
    python wechat_playwright.py --query "新能源车" --limit 3 --headful

Steps:
    1) A Chromium window will open on Sogou search results.
    2) 如出现验证码，请手动完成；完成后返回终端按 Enter 继续。
    3) 脚本会依次打开前 n 条结果，跟随跳转到 mp.weixin.qq.com，提取正文。

Requires: pip install playwright && python -m playwright install chromium
"""

import argparse
import json
import sys
from typing import Any, Dict, List

from playwright.sync_api import sync_playwright, Browser, Page

SEARCH_URL = "https://weixin.sogou.com/weixin"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def open_browser(headless: bool) -> Browser:
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=headless)
    return browser


def fetch_articles(query: str, limit: int, headless: bool) -> List[Dict[str, Any]]:
    browser = open_browser(headless)
    page = browser.new_page(user_agent=USER_AGENT)
    page.goto(f"{SEARCH_URL}?type=2&query={query}", wait_until="networkidle")

    input("如果有验证码，请在浏览器窗口完成后回到终端按 Enter 继续...")

    # 抓取搜索结果卡片
    page.wait_for_timeout(500)
    cards = page.query_selector_all("//a[contains(@id,'sogou_vr_11002601_title_')]")
    articles: List[Dict[str, Any]] = []

    for idx, card in enumerate(cards[:limit]):
        title = card.inner_text().strip()
        href = card.get_attribute("href")
        if not href:
            continue
        if href.startswith("/"):
            href = "https://weixin.sogou.com" + href
        if not href.startswith("http"):
            continue

        # 打开新标签跟随跳转到 mp.weixin.qq.com
        new = browser.new_page(user_agent=USER_AGENT)
        new.goto(href, wait_until="load", timeout=30000)
        final_url = new.url

        # 如果仍然是搜狗反爬页，提示手动处理
        if "antispider" in final_url:
            print(f"[warn] 结果 {idx+1} 命中反爬，请在新标签处理验证码后按 Enter 继续")
            input()
            final_url = new.url

        # 提取正文
        content = ""
        try:
            new.wait_for_selector("#js_content", timeout=8000)
            content = new.inner_text("#js_content").strip()
        except Exception:
            pass

        articles.append(
            {
                "title": title,
                "sogou_link": href,
                "real_url": final_url,
                "content": content,
            }
        )
        new.close()

    browser.close()
    return articles


def main() -> None:
    parser = argparse.ArgumentParser(description="Playwright-based WeChat article fetcher via Sogou.")
    parser.add_argument("-q", "--query", required=True, help="关键词")
    parser.add_argument("-n", "--limit", type=int, default=3, help="抓取条数")
    parser.add_argument("--headful", action="store_true", help="显示浏览器窗口（默认 headless）")
    parser.add_argument("--pretty", action="store_true", help="格式化打印 JSON")
    args = parser.parse_args()

    try:
        articles = fetch_articles(args.query, args.limit, headless=not args.headful)
    except Exception as exc:  # noqa: BLE001
        print(f"Failed: {exc}", file=sys.stderr)
        sys.exit(1)

    indent = 2 if args.pretty else None
    print(json.dumps(articles, ensure_ascii=False, indent=indent))


if __name__ == "__main__":
    main()
