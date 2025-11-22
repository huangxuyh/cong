import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Iterable, Optional

try:  # Allow both "python -m crawler.main" and "python crawler/main.py"
    from .config import DEFAULT_SITE, LOG_DIR, LOG_FILE, SITE_CONFIGS
    from .fetcher import fetch_direct, fetch_via_jina
    from .parser import (
        extract_attachment_links,
        extract_links_from_html,
        extract_links_from_markdown,
        is_article_page,
        is_list_page,
        normalize_url,
        pick_title_from_markdown,
    )
    from .queue_manager import CrawlQueue
    from .storage import save_attachment, save_markdown_article
except ImportError:  # fallback when run as a script without package context
    ROOT = Path(__file__).resolve().parents[1]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from crawler.config import DEFAULT_SITE, LOG_DIR, LOG_FILE, SITE_CONFIGS
    from crawler.fetcher import fetch_direct, fetch_via_jina
    from crawler.parser import (
        extract_attachment_links,
        extract_links_from_html,
        extract_links_from_markdown,
        is_article_page,
        is_list_page,
        normalize_url,
        pick_title_from_markdown,
    )
    from crawler.queue_manager import CrawlQueue
    from crawler.storage import save_attachment, save_markdown_article


def setup_logging() -> None:
    """初始化日志输出到文件与控制台。"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    handlers = [
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ]
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=handlers,
    )


def crawl(
    start_urls: Optional[Iterable[str]], # 起始 URL 列表（通常是列表页或根目录）
    allowed_domains, # 允许爬取的域名白名单（防止跑飞全网）
    article_pattern: str, # 用于匹配「文章页」URL 的正则或字符串模式
    attachment_exts, # 要识别/下载的附件后缀（如 .pdf, .docx 等）
    use_jina: bool, # 是否优先通过 Jina Reader 获取内容（Markdown）
    delay_seconds: float,   # 每次请求之间的延时（防止压垮目标网站）
    max_depth: int,  # 最大爬取深度（BFS 层数限制）
    max_pages: int, # 最大爬取页面数量（全局上限）
    base_url: str, # 站点的 base_url（用于判断列表页等）
    articles_dir: Path, # 文章内容保存目录
    attachments_dir: Path, # 附件保存目录
) -> None:
    """基于站点配置的 BFS 爬取核心流程。"""
    queue = CrawlQueue()
    for url in start_urls or []:
        normalized = normalize_url(url, allowed_domains)
        if normalized:
            queue.add(normalized, depth=0)

    while True:
        item = queue.pop()
        if not item:
            break
        url, depth = item
        if url in queue.visited:
            continue
        if depth > max_depth:
            continue
        if len(queue.visited) >= max_pages:
            logging.info("Reached max pages limit: %s", max_pages)
            break

        queue.mark_visited(url)
        logging.info("Crawl #%s depth=%s url=%s", len(queue.visited), depth, url)

        # Fetch via Jina first, fallback to direct HTML
        page_text = None
        content_is_md = False
        if use_jina:
            page_text = fetch_via_jina(url)
            content_is_md = page_text is not None
        if page_text is None:
            page_text = fetch_direct(url)
            content_is_md = False
        if page_text is None:
            continue

        # Download attachments if any
        for att_url in extract_attachment_links(page_text, attachment_exts):
            save_attachment(att_url, output_dir=attachments_dir, referer=url)

        # Handle article or list
        if is_article_page(url, article_pattern):
            title = pick_title_from_markdown(page_text, url) if content_is_md else url
            save_markdown_article(url, title, page_text, output_dir=articles_dir)
        elif is_list_page(url, base_url, article_pattern):
            if content_is_md:
                links = extract_links_from_markdown(page_text, allowed_domains, attachment_exts)
            else:
                links = extract_links_from_html(page_text, base=url, allowed_domains=allowed_domains, attachment_exts=attachment_exts)
            for link in links:
                queue.add(link, depth + 1)

        time.sleep(delay_seconds)

    logging.info("Crawling complete. Visited %s pages.", len(queue.visited))


def main() -> None:
    """入口：读取站点配置，设置输出目录并启动爬取。"""
    parser = argparse.ArgumentParser(description="Generic crawler with site configs.")
    parser.add_argument("--site", default=DEFAULT_SITE, choices=list(SITE_CONFIGS.keys()), help="Site key to crawl")
    args = parser.parse_args()

    cfg = SITE_CONFIGS.get(args.site)
    if not cfg:
        raise SystemExit(f"Unknown site {args.site}")

    setup_logging()
    # Per-site output dirs
    from config import get_output_dirs

    articles_dir, attachments_dir = get_output_dirs(args.site)

    crawl(
        start_urls=cfg["start_urls"],
        allowed_domains=cfg["allowed_domains"],
        article_pattern=cfg.get("article_pattern", ""),
        attachment_exts=cfg.get("attachment_exts", ()),
        use_jina=cfg.get("use_jina", False),
        delay_seconds=cfg.get("delay_seconds", 1.0),
        max_depth=cfg.get("max_depth", 2),
        max_pages=cfg.get("max_pages", 200),
        base_url=cfg["base_url"],
        articles_dir=articles_dir,
        attachments_dir=attachments_dir,
    )


if __name__ == "__main__":
    main()
