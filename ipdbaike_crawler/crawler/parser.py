import re
from typing import Iterable, List
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .config import ARTICLE_PATTERN, ATTACHMENT_PATTERN, ATTACHMENT_EXTS, BASE_URL


def normalize_url(url: str) -> str:
    """Normalize in-domain URL: strip fragments and trailing slash."""
    parsed = urlparse(url)
    if parsed.netloc and "ipdbaike.com" not in parsed.netloc:
        return ""
    clean = parsed._replace(fragment="")
    normalized = clean.geturl()
    if normalized.endswith("/") and not normalized.endswith("//"):
        normalized = normalized[:-1]
    return normalized


def looks_like_asset(url: str) -> bool:
    lower = url.lower()
    return any(lower.endswith(ext) for ext in ATTACHMENT_EXTS) or "/static/" in lower or "/images/" in lower


def extract_links_from_markdown(md: str) -> List[str]:
    """
    Pull links from markdown text (both markdown links and bare URLs).
    """
    candidates = set()
    # Markdown links: [text](url "title")
    candidates.update(re.findall(r"\((https?://ipdbaike\.com[^\s)]+)\)", md))
    # Bare URLs in text
    candidates.update(re.findall(r"https?://ipdbaike\.com[^\s)]+", md))

    links: List[str] = []
    for raw in candidates:
        normalized = normalize_url(raw.split("#")[0])
        if not normalized or looks_like_asset(normalized):
            continue
        links.append(normalized)
    return links


def extract_links_from_html(html: str, base: str = BASE_URL) -> List[str]:
    """Extract anchor links from HTML (absolute join)."""
    soup = BeautifulSoup(html, "html.parser")
    links: List[str] = []
    seen = set()
    for a in soup.find_all("a", href=True):
        raw = urljoin(base, a["href"])
        normalized = normalize_url(raw.split("#")[0])
        if not normalized or normalized in seen or looks_like_asset(normalized):
            continue
        seen.add(normalized)
        links.append(normalized)
    return links


def is_article_page(url: str) -> bool:
    return re.search(ARTICLE_PATTERN, url) is not None


def is_list_page(url: str) -> bool:
    return url.startswith(BASE_URL) and not is_article_page(url)


def extract_attachment_links(text: str) -> List[str]:
    return re.findall(ATTACHMENT_PATTERN, text)


def pick_title_from_markdown(md: str, default: str) -> str:
    """Get title from markdown 'Title:' header or first heading."""
    match = re.search(r"^Title:\s*(.+)$", md, re.M)
    if match:
        return match.group(1).strip()
    heading = re.search(r"^#\s+(.+)$", md, re.M)
    if heading:
        return heading.group(1).strip()
    return default
