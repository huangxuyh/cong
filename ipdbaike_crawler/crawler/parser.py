import re
from typing import Iterable, List
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup


def normalize_url(url: str, allowed_domains: Iterable[str]) -> str:
    """
    归一化 URL，过滤域名、去除片段和末尾斜杠差异。
    - allowed_domains 为空则不限制域名；否则只保留 netloc 中包含任一域名的链接。
    - 返回空字符串表示被过滤。
    """
    parsed = urlparse(url)  # 结构化拆解 URL
    if parsed.netloc and allowed_domains:
        if not any(dom in parsed.netloc for dom in allowed_domains):  # 域名不在白名单
            return ""
    clean = parsed._replace(fragment="")  # 去掉 # 片段
    normalized = clean.geturl()  # 重新拼装
    if normalized.endswith("/") and not normalized.endswith("//"):  # 去掉末尾单斜杠
        normalized = normalized[:-1]
    return normalized  # 可能为空


def looks_like_asset(url: str, attachment_exts: Iterable[str]) -> bool:
    """
    判断是否为静态资源/附件。
    - 依据附件后缀或常见静态路径 (/static/、/images/) 过滤。
    """
    lower = url.lower()
    return any(lower.endswith(ext) for ext in attachment_exts) or "/static/" in lower or "/images/" in lower


def extract_links_from_markdown(md: str, allowed_domains: Iterable[str], attachment_exts: Iterable[str]) -> List[str]:
    """
    从 markdown 文本中抽取站内链接（含 markdown 链接与裸 URL），过滤静态资源与跨域。
    - 适用于 Jina 返回的 markdown。
    - 返回已归一化且去重后的链接列表。
    """
    domain_pattern = "|".join(re.escape(d) for d in allowed_domains) if allowed_domains else r".+"
    candidates = set()  # 用集合做去重
    candidates.update(re.findall(rf"\((https?://(?:{domain_pattern})[^\s)]+)\)", md))  # markdown 链接
    candidates.update(re.findall(rf"https?://(?:{domain_pattern})[^\s)]+", md))  # 裸 URL

    links: List[str] = []
    for raw in candidates:
        normalized = normalize_url(raw.split("#")[0], allowed_domains)  # 去片段再归一化
        if not normalized or looks_like_asset(normalized, attachment_exts):  # 过滤空/静态资源
            continue
        links.append(normalized)
    return links


def extract_links_from_html(
    html: str, base: str, allowed_domains: Iterable[str], attachment_exts: Iterable[str]
) -> List[str]:
    """
    从 HTML 抽取站内链接，转绝对路径，过滤静态资源与跨域，返回去重列表。
    """
    soup = BeautifulSoup(html, "html.parser")  # 解析 HTML
    links: List[str] = []
    seen = set()  # 去重集合
    for a in soup.find_all("a", href=True):  # 遍历所有带 href 的 <a>
        raw = urljoin(base, a["href"])  # 相对转绝对
        normalized = normalize_url(raw.split("#")[0], allowed_domains)  # 去片段+过滤域
        if not normalized or normalized in seen or looks_like_asset(normalized, attachment_exts):
            continue  # 跳过空、重复、静态资源
        seen.add(normalized)
        links.append(normalized)
    return links


def is_article_page(url: str, article_pattern: str) -> bool:
    """
    根据正则判定是否文章页；若正则为空则默认都视为文章。
    """
    return re.search(article_pattern, url) is not None if article_pattern else True


def is_list_page(url: str, base_url: str, article_pattern: str) -> bool:
    """
    列表页判定：需以 base_url 开头且未命中文章正则。
    """
    return url.startswith(base_url) and not is_article_page(url, article_pattern)


def extract_attachment_links(text: str, attachment_exts: Iterable[str]) -> List[str]:
    """
    按附件后缀匹配文本中的下载链接，后缀为空则返回空列表。
    """
    if not attachment_exts:
        return []
    # 构造正则表达式：
    # r"https?://[^\s\"']+(?:%s)" 这一部分是一个字符串模板，%s 会被后面的 join(...) 替换
    #
    # 1) "https?://"：
    #    - 匹配以 http:// 或 https:// 开头的 URL
    #
    # 2) "[^\\s\"']+"：
    #    - 匹配至少一个“非空白且不是双引号/单引号”的字符
    #    - 也就是 URL 主体部分（直到遇到空格或引号为止）
    #
    # 3) "(?:%s)"：
    #    - 非捕获分组，用来放后缀部分的正则，比如：(\.pdf|\.docx|\.xls)
    #
    # "|".join(re.escape(ext) for ext in attachment_exts)：
    #    - 对每个后缀（例如 ".pdf"）做 re.escape，避免其中的点等特殊字符被当作正则元字符
    #    - 然后用 "|" 连接成："\.pdf|\.docx|\.xls" 这样的形式
    #
    # 最终 pattern 示例：
    #   如果 attachment_exts = [".pdf", ".docx"]
    #   pattern = r"https?://[^\s\"']+(?:\.pdf|\.docx)"
    pattern = r"https?://[^\s\"']+(?:%s)" % "|".join(re.escape(ext) for ext in attachment_exts)
    return re.findall(pattern, text)


def pick_title_from_markdown(md: str, default: str) -> str:
    """
    从 markdown 中提取标题：
    - 优先匹配 'Title:' 行
    - 其次匹配首个一级标题 '# ...'
    - 都失败时返回默认值
    """
    match = re.search(r"^Title:\s*(.+)$", md, re.M)
    if match:
        return match.group(1).strip()
    heading = re.search(r"^#\s+(.+)$", md, re.M)
    if heading:
        return heading.group(1).strip()
    return default
