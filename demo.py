import os
import time
import logging
import re
from collections import deque
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# ---- ???? ----
BASE_URL = "https://ipdbaike.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
DELAY_SECONDS = 1.0
OUTPUT_DIR = "ipdbaike_articles_jina"
START_URLS = [
    "https://ipdbaike.com/",
    "https://ipdbaike.com/?strategic/",
    "https://ipdbaike.com/?planning/",
    "https://ipdbaike.com/?process/",
    "https://ipdbaike.com/?project/",
    "https://ipdbaike.com/?performance/",
    "https://ipdbaike.com/?role/",
    "https://ipdbaike.com/?zixun/",
    "https://ipdbaike.com/?zxyw/",
    "https://ipdbaike.com/?zjtj/",
    "https://ipdbaike.com/?download/",
]
MAX_PAGES = 200  # ?????????????

# Jina Reader ??
JINA_PREFIX = "https://r.jina.ai/"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ??????
os.makedirs(OUTPUT_DIR, exist_ok=True)


def fetch_via_jina(url: str) -> str | None:
    """?? Jina Reader ?? markdown ????????? None?"""
    jinau = JINA_PREFIX + url
    try:
        resp = requests.get(jinau, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        logging.info(f"Jina fetch successful for {url}")
        return resp.text
    except requests.exceptions.SSLError as e:
        logging.error(f"SSL error in Jina fetch for {url}: {e}")
    except requests.exceptions.ConnectionError as e:
        logging.error(f"Connection error in Jina fetch for {url}: {e}")
    except requests.exceptions.Timeout as e:
        logging.error(f"Timeout in Jina fetch for {url}: {e}")
    except Exception as e:
        logging.error(f"Other error in Jina fetch for {url}: {e}")
    return None


def normalize_url(url: str) -> str:
    """?????????????????????"""
    parsed = urlparse(url)
    if parsed.netloc and "ipdbaike.com" not in parsed.netloc:
        return ""
    clean = parsed._replace(fragment="")
    normalized = clean.geturl()
    if normalized.endswith("/") and not normalized.endswith("//"):
        normalized = normalized[:-1]
    return normalized


def looks_like_asset(url: str) -> bool:
    """???????????????????"""
    lower = url.lower()
    return any(
        lower.endswith(ext)
        for ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".css", ".js", ".zip", ".rar", ".pdf")
    ) or "/static/" in lower or "/images/" in lower


def extract_links_from_md(md_text: str) -> list[str]:
    """? Jina markdown ?????????????????"""
    candidates: set[str] = set()
    for _, href in re.findall(r"\[([^\]]+)\]\((https://ipdbaike\.com/[^\s)]+)\)", md_text):
        candidates.add(href)
    for href in re.findall(r"https://ipdbaike\.com/[^\s)]+", md_text):
        candidates.add(href)

    links: list[str] = []
    for raw in candidates:
        url = normalize_url(raw.split("#")[0])
        if not url or looks_like_asset(url):
            continue
        links.append(url)
    return links


def save_article(url: str, title: str, content: str) -> None:
    """???????? Markdown ???"""
    safe_title = "".join(c if (c.isalnum() or c in (" ", "_", "-")) else "_" for c in title).strip()
    filename = f"{safe_title}.md"
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"# {title}

")
        f.write(f"URL: {url}

")
        f.write(content)
    logging.info(f"Saved article: {title} -> {filepath}")


def fetch_and_save_page(url: str) -> list[str]:
    """???????????????????????"""
    md_content = fetch_via_jina(url)
    if not md_content:
        logging.warning(f"Skip {url}, Jina content missing")
        return []

    title_match = re.search(r"^Title:\s*(.+)$", md_content, re.M)
    title = title_match.group(1).strip() if title_match else url
    save_article(url, title, md_content)
    return extract_links_from_md(md_content)


def crawl_site(start_urls: list[str], max_pages: int = MAX_PAGES) -> None:
    """??????????? Jina ?? 403?"""
    visited: set[str] = set()
    queue: deque[str] = deque(normalize_url(u) for u in start_urls)
    while queue and len(visited) < max_pages:
        url = queue.popleft()
        if not url or url in visited:
            continue
        visited.add(url)
        logging.info(f"Crawl #{len(visited)}: {url}")
        try:
            links = fetch_and_save_page(url)
        except Exception as e:
            logging.error(f"Error processing {url}: {e}")
            links = []
        for link in links:
            if link not in visited:
                queue.append(link)
        time.sleep(DELAY_SECONDS)
    logging.info(f"Crawl finished. Visited {len(visited)} pages.")


def parse_list_page(list_url: str):
    """
    ???????????? (title, href) ????????
    """
    try:
        resp = requests.get(list_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        logging.error(f"List page request failed for {list_url}: {e}")
        return []
    items = []
    for a in soup.select("div.post-item a"):
        title = a.get_text(strip=True)
        href = a.get("href")
        if href:
            full = urljoin(BASE_URL, href)
            items.append((title, full))
    logging.info(f"Found {len(items)} items on list page {list_url}")
    return items


def main():
    # ???? BFS ?????????????? parse_list_page?
    crawl_site(START_URLS, max_pages=MAX_PAGES)


if __name__ == "__main__":
    main()
