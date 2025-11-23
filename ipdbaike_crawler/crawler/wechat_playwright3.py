"""
Use Playwright to fetch WeChat articles via Sogou with a real browser.

- 支持在浏览器里手动过一次验证码，随后自动保存 Cookie 到文件（默认 cookies.txt），供 requests 脚本复用。
- 自动点击前 N 条结果，跳转到 mp.weixin.qq.com，提取正文并打印 JSON。

Usage (run from repo root or crawler/ dir):
    python wechat_playwright.py --query "新能源车" --limit 3 --headful --cookie-file cookies.txt

Requires:
    pip install playwright
    python -m playwright install chromium
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from playwright.sync_api import Browser, Page, sync_playwright

SEARCH_URL = "https://weixin.sogou.com/weixin"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def open_browser(headless: bool) -> Browser:
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=headless)
    return browser


def save_cookies_header(page: Page, cookie_file: Path) -> None:
    """提取搜狗/微信相关 Cookie，保存为一行 Cookie 头，供 requests 复用。"""
    cookies = page.context.cookies()
    wanted = {}
    for c in cookies:
        domain = c.get("domain", "")
        if "weixin.sogou.com" in domain or "mp.weixin.qq.com" in domain:
            wanted[c["name"]] = c["value"]
    if not wanted:
        print("未找到搜狗/微信的 Cookie，可能仍需验证码或刷新页面后再试。")
        return
    header = "; ".join(f"{k}={v}" for k, v in wanted.items())
    cookie_file.write_text(header, encoding="utf-8")
    print(f"Cookie 已保存到 {cookie_file}")


def fetch_articles(query: str, limit: int, headless: bool, cookie_file: Path) -> List[Dict[str, Any]]:
    browser = open_browser(headless)
    context = browser.new_context(user_agent=USER_AGENT)
    page = context.new_page()
    page.goto(f"{SEARCH_URL}?type=2&query={query}", wait_until="networkidle")

    input("如果有验证码，请在浏览器窗口完成后回到终端按 Enter 继续...")
    save_cookies_header(page, cookie_file)

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
        new = context.new_page()
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
    parser.add_argument(
        "--cookie-file", default="cookies.txt", help="持久化 Cookie 文件（默认 cookies.txt，与 wechat_search.py 复用）"
    )
    parser.add_argument("--pretty", action="store_true", help="格式化打印 JSON")
    args = parser.parse_args()

    try:
        cookie_path = Path(args.cookie_file).resolve()
        articles = fetch_articles(args.query, args.limit, headless=not args.headful, cookie_file=cookie_path)
    except Exception as exc:  # noqa: BLE001
        print(f"Failed: {exc}", file=sys.stderr)
        sys.exit(1)

    indent = 2 if args.pretty else None
    print(json.dumps(articles, ensure_ascii=False, indent=indent))


if __name__ == "__main__":
    main()
