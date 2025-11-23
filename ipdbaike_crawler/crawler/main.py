import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Iterable, Optional

try:  # 兼容两种运行方式：python -m crawler.main 或 python crawler/main.py
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
except ImportError:
    # 当作脚本运行时，手动把包路径加入 sys.path
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
    """初始化日志输出到文件与控制台，便于调试与留痕。"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)  # 确保日志目录存在
    handlers = [
        logging.FileHandler(LOG_FILE, encoding="utf-8"),  # 写入文件
        logging.StreamHandler(),  # 同步打印到 stdout
    ]
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=handlers,
    )


def crawl(
    start_urls: Optional[Iterable[str]],  # 入口 URL 列表
    allowed_domains,  # 允许的域名白名单
    article_pattern: str,  # 文章页匹配正则
    attachment_exts,  # 需要下载的附件后缀
    use_jina: bool,  # 是否优先走 Jina
    delay_seconds: float,  # 抓取间隔秒数
    max_depth: int,  # 最大抓取深度（入口为 0）
    max_pages: int,  # 最大抓取页面数量
    base_url: str,  # 基准 URL，用于判定列表页
    articles_dir: Path,  # 文章输出目录
    attachments_dir: Path,  # 附件输出目录
) -> None:
    """
    按站点配置执行 BFS 爬取：
    出队 -> 判重/深度/上限 -> 抓取 (Jina/直连) -> 附件 -> 文章或列表 -> 新链接入队。
    """
    queue = CrawlQueue()  # 初始化队列/visited
    for url in start_urls or []:  # 遍历入口 URL
        normalized = normalize_url(url, allowed_domains)  # 过滤域名并归一化
        if normalized:
            queue.add(normalized, depth=0)  # 深度 0 入队

    while True:
        item = queue.pop()  # 出队一个 (url, depth)
        if not item:
            break  # 队列空，结束
        url, depth = item
        if url in queue.visited:
            continue  # 已访问，跳过
        if depth > max_depth:
            continue  # 超过深度限制
        if len(queue.visited) >= max_pages:
            logging.info("Reached max pages limit: %s", max_pages)
            break  # 达到页数上限

        queue.mark_visited(url)  # 标记已访问
        logging.info("Crawl #%s depth=%s url=%s", len(queue.visited), depth, url)

        # 抓取页面：优先 Jina，失败回落直连
        page_text = None
        content_is_md = False  # 标记内容是否为 markdown
        if use_jina:
            page_text = fetch_via_jina(url)
            content_is_md = page_text is not None
        if page_text is None:
            page_text = fetch_direct(url)
            content_is_md = False
        if page_text is None:
            continue  # 两种方式都失败，跳过

        # 抓附件（基于后缀匹配）,extract_attachment_links会对 page_text进行正则匹配，根据附件后缀来抽取所有匹配的下载链接
        for att_url in extract_attachment_links(page_text, attachment_exts):
            save_attachment(att_url, output_dir=attachments_dir, referer=url) # 负责实际下载文件并保存到attachments_dir

        # 分支：文章页保存 / 列表页继续下钻
        if is_article_page(url, article_pattern):
            title = pick_title_from_markdown(page_text, url) if content_is_md else url
            save_markdown_article(url, title, page_text, output_dir=articles_dir)
        elif is_list_page(url, base_url, article_pattern):
            if content_is_md:
                links = extract_links_from_markdown(page_text, allowed_domains, attachment_exts)
            else:
                links = extract_links_from_html(
                    page_text, base=url, allowed_domains=allowed_domains, attachment_exts=attachment_exts
                )
            for link in links:
                queue.add(link, depth + 1)  # 下一层深度入队

        time.sleep(delay_seconds)  # 节流

    logging.info("Crawling complete. Visited %s pages.", len(queue.visited))


def main() -> None:
    """入口：解析站点参数，加载配置，设置输出目录并启动爬取。"""
    parser = argparse.ArgumentParser(description="Generic crawler with site configs.")
    parser.add_argument("--site", default=DEFAULT_SITE, choices=list(SITE_CONFIGS.keys()), help="Site key to crawl")
    args = parser.parse_args()  # 解析命令行参数

    cfg = SITE_CONFIGS.get(args.site)  # 获取站点配置
    if not cfg:
        raise SystemExit(f"Unknown site {args.site}")

    setup_logging()  # 初始化日志
    from config import get_output_dirs  # 延迟导入，避免循环

    articles_dir, attachments_dir = get_output_dirs(args.site)  # 按站点生成输出目录

    # 启动爬取，所有参数来自站点配置
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
    main()  # 支持直接运行文件启动爬虫
