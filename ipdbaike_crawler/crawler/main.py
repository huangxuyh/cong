import logging
import time
from pathlib import Path
from typing import Iterable, List, Optional

try:  # Allow both "python -m crawler.main" and "python crawler/main.py"
    from .config import (
        BASE_URL,
        DELAY_SECONDS,
        LOG_DIR,
        LOG_FILE,
        MAX_DEPTH,
        MAX_PAGES,
        START_URLS,
    )
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
    import sys
    from pathlib import Path

    ROOT = Path(__file__).resolve().parents[1]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from crawler.config import (
        BASE_URL,
        DELAY_SECONDS,
        LOG_DIR,
        LOG_FILE,
        MAX_DEPTH,
        MAX_PAGES,
        START_URLS,
    )
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


def crawl(start_urls: Optional[Iterable[str]] = None, max_depth: int = MAX_DEPTH, max_pages: int = MAX_PAGES) -> None:
    queue = CrawlQueue()
    for url in start_urls or START_URLS:
        normalized = normalize_url(url)
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
        page_text = fetch_via_jina(url)
        content_is_md = page_text is not None
        if page_text is None:
            page_text = fetch_direct(url)
            content_is_md = False
        if page_text is None:
            continue

        # Download attachments if any
        for att_url in extract_attachment_links(page_text):
            save_attachment(att_url, referer=url)

        # Handle article or list
        if is_article_page(url):
            title = pick_title_from_markdown(page_text, url) if content_is_md else url
            save_markdown_article(url, title, page_text)
        elif is_list_page(url):
            if content_is_md:
                links = extract_links_from_markdown(page_text)
            else:
                links = extract_links_from_html(page_text, base=url)
            for link in links:
                queue.add(link, depth + 1)

        time.sleep(DELAY_SECONDS)

    logging.info("Crawling complete. Visited %s pages.", len(queue.visited))


def main() -> None:
    setup_logging()
    crawl()


if __name__ == "__main__":
    main()
