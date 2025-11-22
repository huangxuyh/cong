import re
from typing import Iterable, List
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup


def normalize_url(url: str, allowed_domains: Iterable[str]) -> str:
    """归一化 URL：过滤域名、去掉锚点与末尾斜杠差异。"""
    parsed = urlparse(url)
    if parsed.netloc and allowed_domains:
        if not any(dom in parsed.netloc for dom in allowed_domains):
            return ""
    clean = parsed._replace(fragment="")
    normalized = clean.geturl()
    if normalized.endswith("/") and not normalized.endswith("//"):
        normalized = normalized[:-1]
    return normalized


def looks_like_asset(url: str, attachment_exts: Iterable[str]) -> bool:
    """判断是否为静态资源/附件，避免加入后续抓取。"""
    lower = url.lower()
    return any(lower.endswith(ext) for ext in attachment_exts) or "/static/" in lower or "/images/" in lower


def extract_links_from_markdown(md: str, allowed_domains: Iterable[str], attachment_exts: Iterable[str]) -> List[str]:
    """
    从 markdown 中抽取站内链接（含裸 URL），过滤静态资源与跨域。
    """
    domain_pattern = "|".join(re.escape(d) for d in allowed_domains) if allowed_domains else r".+"
    candidates = set()
    candidates.update(re.findall(rf"\((https?://(?:{domain_pattern})[^\s)]+)\)", md))
    candidates.update(re.findall(rf"https?://(?:{domain_pattern})[^\s)]+", md))

    links: List[str] = []
    for raw in candidates:
        normalized = normalize_url(raw.split("#")[0], allowed_domains)
        if not normalized or looks_like_asset(normalized, attachment_exts):
            continue
        links.append(normalized)
    return links


def extract_links_from_html(
    html: str, base: str, allowed_domains: Iterable[str], attachment_exts: Iterable[str]
) -> List[str]:
    """从 HTML 抽取站内链接，绝对化并过滤静态资源/跨域。"""
    soup = BeautifulSoup(html, "html.parser")
    links: List[str] = []
    seen = set()
    for a in soup.find_all("a", href=True):
        raw = urljoin(base, a["href"])
        normalized = normalize_url(raw.split("#")[0], allowed_domains)
        if not normalized or normalized in seen or looks_like_asset(normalized, attachment_exts):
            continue
        seen.add(normalized)
        links.append(normalized)
    return links


def is_article_page(url: str, article_pattern: str) -> bool:
    """根据正则判定是否为文章页，空正则则全部视为文章。"""
    return re.search(article_pattern, url) is not None if article_pattern else True


def is_list_page(url: str, base_url: str, article_pattern: str) -> bool:
    return url.startswith(base_url) and not is_article_page(url, article_pattern)


def extract_attachment_links(text: str, attachment_exts: Iterable[str]) -> List[str]:
    """根据附件后缀匹配文本中的下载链接。"""
    if not attachment_exts:
        return []
    pattern = r"https?://[^\s\"']+(?:%s)" % "|".join(re.escape(ext) for ext in attachment_exts)
    return re.findall(pattern, text)


def pick_title_from_markdown(md: str, default: str) -> str:
    """尝试从 markdown 的 Title/首级标题提取标题，失败则返回默认值。"""
    match = re.search(r"^Title:\s*(.+)$", md, re.M)
    if match:
        return match.group(1).strip()
    heading = re.search(r"^#\s+(.+)$", md, re.M)
    if heading:
        return heading.group(1).strip()
    return default
