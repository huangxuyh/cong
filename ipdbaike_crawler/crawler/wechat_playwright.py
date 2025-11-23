"""
基于 Playwright 的搜狗多模式抓取：
- wechat：搜狗微信搜索 -> 跳转 mp.weixin.qq.com -> 抽取正文，并保存 Cookie（cookies.txt）。
- zhihu：搜狗知乎站内搜索 -> 抽取标题和链接（站点：zhihu.sogou.com 或 sogou insite）。
- image：搜狗图片搜索 -> 抽取缩略图/原图，并下载到本地（自动推断后缀）。

遇到反爬（antispider 或无结果）时才提示人工在浏览器完成验证后按 Enter。

示例：
  python wechat_playwright.py --mode wechat --query "新能源车" --limit 3 --headful --cookie-file cookies.txt
  python wechat_playwright.py --mode zhihu  --query "新能源车" --limit 3 --pretty
  python wechat_playwright.py --mode image  --query "新能源车" --limit 5 --image-dir output/images_download --pretty

依赖：
  pip install playwright requests
  python -m playwright install chromium
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlencode, quote_plus

import requests
from playwright.sync_api import Browser, Page, sync_playwright

SEARCH_URL_WECHAT = "https://weixin.sogou.com/weixin"
SEARCH_URL_ZHIHU = "https://zhihu.sogou.com/zhihu"
SEARCH_URL_IMAGE = "https://pic.sogou.com/pics"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


# 启动浏览器
def open_browser(headless: bool) -> Browser:
    """启动 Chromium 浏览器（可选无头模式），返回 browser 对象。"""
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=headless)
    return browser


# 保存搜狗/微信 Cookie
def save_cookies_header(page: Page, cookie_file: Path) -> None:
    """提取 weixin.sogou.com / mp.weixin.qq.com 的 Cookie，保存为一行 Cookie 头。"""
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


# 反爬处理
def handle_antispider(page: Page, cookie_file: Path, selector: str) -> None:
    """若页面命中 antispider 或无目标元素，则提示人工验证后重载并保存 Cookie。"""
    if ("antispider" in page.url) or (not page.query_selector_all(selector)):
        print("[warn] 可能触发反爬，请在浏览器完成验证码后按 Enter 继续")
        input()
        save_cookies_header(page, cookie_file)
        page.wait_for_timeout(500)
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(500)


# 微信：搜狗 -> 微信正文
def fetch_wechat_articles(query: str, limit: int, headless: bool, cookie_file: Path) -> List[Dict[str, Any]]:
    browser = open_browser(headless)
    context = browser.new_context(user_agent=USER_AGENT)
    page = context.new_page()
    page.goto(f"{SEARCH_URL_WECHAT}?type=2&query={query}", wait_until="networkidle")

    save_cookies_header(page, cookie_file)
    handle_antispider(page, cookie_file, "//a[contains(@id,'sogou_vr_11002601_title_')]")

    cards = page.query_selector_all("//a[contains(@id,'sogou_vr_11002601_title_')]")
    articles: List[Dict[str, Any]] = []

    for idx, card in enumerate(cards[:limit]):
        title = card.inner_text().strip()
        href = card.get_attribute("href") or ""
        if href.startswith("/"):
            href = "https://weixin.sogou.com" + href
        if not href.startswith("http"):
            continue

        new = context.new_page()
        new.goto(href, wait_until="load", timeout=30000)
        final_url = new.url

        if "antispider" in final_url:
            print(f"[warn] 结果 {idx+1} 命中反爬，请在新标签处理验证码后按 Enter 继续")
            input()
            final_url = new.url

        content = ""
        try:
            new.wait_for_selector("#js_content", timeout=8000)
            content = new.inner_text("#js_content").strip()
        except Exception:
            pass

        articles.append({"title": title, "sogou_link": href, "real_url": final_url, "content": content})
        new.close()

    browser.close()
    return articles


# 知乎：搜狗站内搜索
def fetch_zhihu(query: str, limit: int, headless: bool) -> List[Dict[str, Any]]:
    """
    使用 Playwright 抓取搜狗知乎站内搜索结果，返回标题和链接。
    """
    browser = open_browser(headless)
    context = browser.new_context(user_agent=USER_AGENT)
    page = context.new_page()
    params = urlencode({"query": query, "ie": "utf8", "insite": "zhihu.com"})
    page.goto(f"{SEARCH_URL_ZHIHU}?{params}", wait_until="networkidle")

    if ("antispider" in page.url) or (not page.query_selector_all("h3 a")):
        print("[warn] 知乎搜索可能触发反爬，请在浏览器完成验证后按 Enter 继续")
        input()
        page.wait_for_timeout(500)
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(500)

    results: List[Dict[str, Any]] = []
    anchors = page.query_selector_all("h3 a") or page.query_selector_all(".results h3 a") or []
    # 兜底：抓取指向 zhihu.com 的链接
    if not anchors:
        anchors = page.query_selector_all("a[href^='https://www.zhihu.com']") or []
    for a in anchors:
        title = a.inner_text().strip()
        href = a.get_attribute("href") or ""
        if not href.startswith("http"):
            continue
        results.append({"title": title, "link": href})
        if len(results) >= limit:
            break

    browser.close()
    return results


# 图片：搜狗图片搜索 + 下载
def fetch_images(query: str, limit: int, headless: bool, download_dir: Path) -> List[Dict[str, Any]]:
    """
    使用 Playwright 抓取搜狗图片搜索结果，并下载到本地。
    - 过滤 data: 和无协议链接
    - 尝试根据 URL 或 Content-Type 推断后缀，默认 .jpg
    """
    browser = open_browser(headless)
    context = browser.new_context(user_agent=USER_AGENT)
    page = context.new_page()
    page.goto(f"{SEARCH_URL_IMAGE}?query={quote_plus(query)}", wait_until="networkidle")

    if ("antispider" in page.url) or (not page.query_selector_all("img")):
        print("[warn] 图片搜索可能触发反爬，请在浏览器完成验证后按 Enter 继续")
        input()
        page.wait_for_timeout(500)
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(500)

    download_dir.mkdir(parents=True, exist_ok=True)
    results: List[Dict[str, Any]] = []
    for idx, img in enumerate(page.query_selector_all("img")):
        thumb = img.get_attribute("src") or img.get_attribute("data-original") or img.get_attribute("data-src")
        if not thumb or thumb.startswith("data:"):
            continue
        if thumb.startswith("//"):
            thumb = "https:" + thumb
        original = img.get_attribute("data-original") or thumb
        if original.startswith("//"):
            original = "https:" + original

        record: Dict[str, Any] = {"thumb": thumb, "original": original}
        # 下载图片并推断后缀
        try:
            r = requests.get(
                original,
                headers={"User-Agent": USER_AGENT, "Referer": "https://pic.sogou.com/"},
                timeout=15,
            )
            r.raise_for_status()
            # 后缀推断：优先 URL 中的 .xxx，其次 Content-Type
            namepart = thumb.split("/")[-1].split("?")[0] or f"image_{idx}"
            ext = ""
            if "." in namepart and len(namepart.rsplit(".", 1)[-1]) <= 5:
                namepart, ext = namepart.rsplit(".", 1)
                ext = "." + ext
            if not ext:
                ctype = r.headers.get("content-type", "").lower()
                if "png" in ctype:
                    ext = ".png"
                elif "gif" in ctype:
                    ext = ".gif"
                elif "webp" in ctype:
                    ext = ".webp"
                else:
                    ext = ".jpg"
            fname = (namepart or f"image_{idx}") + ext
            path = download_dir / fname
            path.write_bytes(r.content)
            record["saved_path"] = str(path)
        except Exception as e:
            record["error"] = str(e)
        results.append(record)
        if len(results) >= limit:
            break

    browser.close()
    return results


def main() -> None:
    """解析命令行参数，根据模式执行微信/知乎/图片抓取，并打印 JSON。"""
    parser = argparse.ArgumentParser(description="Sogou-based fetcher via Playwright (WeChat/Zhihu/Image).")
    parser.add_argument("-q", "--query", required=True, help="关键词")
    parser.add_argument("-n", "--limit", type=int, default=3, help="抓取条数")
    parser.add_argument("--mode", choices=["wechat", "zhihu", "image"], default="wechat", help="抓取模式")
    parser.add_argument("--headful", action="store_true", help="显示浏览器窗口（默认无头）")
    parser.add_argument(
        "--cookie-file",
        default="cookies.txt",
        help="(wechat) 持久化 Cookie 文件（默认 cookies.txt，与 wechat_search.py 复用）",
    )
    parser.add_argument(
        "--image-dir",
        default="output/images_download",
        help="(image) 图片保存目录，默认 output/images_download",
    )
    parser.add_argument("--pretty", action="store_true", help="格式化打印 JSON")
    args = parser.parse_args()

    try:
        if args.mode == "wechat":
            cookie_path = Path(args.cookie_file).resolve()
            data = fetch_wechat_articles(args.query, args.limit, headless=not args.headful, cookie_file=cookie_path)
        elif args.mode == "zhihu":
            data = fetch_zhihu(args.query, args.limit, headless=not args.headful)
        else:  # image
            download_dir = Path(args.image_dir).resolve()
            data = fetch_images(args.query, args.limit, headless=not args.headful, download_dir=download_dir)
    except Exception as exc:
        print(f"Failed: {exc}", file=sys.stderr)
        sys.exit(1)

    indent = 2 if args.pretty else None
    print(json.dumps(data, ensure_ascii=False, indent=indent))


if __name__ == "__main__":
    main()
