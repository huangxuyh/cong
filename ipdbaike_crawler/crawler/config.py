from pathlib import Path

# 全局头部与 Jina 前缀配置（Jina 用于绕过部分站点的 403）
# 如目标站点对 UA/语言敏感，可在 SITE_CONFIGS 中覆盖 HEADERS，再传入 fetcher。
JINA_PREFIX = "https://r.jina.ai/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

# 站点配置：可按模板新增其他站点，推荐保持小写 key 方便命令行传参
# 字段说明：
#   base_url：站点基准 URL（用于列表判断）
#   start_urls：入口列表（可多入口并行 BFS）
#   allowed_domains：允许的域名（过滤外链，只保留包含任一域名的链接）
#   use_jina：是否优先走 Jina 代理（适合 403/反爬严重的站点）
#   article_pattern：文章页正则（匹配成功视为终点，保存内容）
#   max_depth：BFS 深度控制（入口=0）
#   max_pages：最大抓取页数（全局保险丝）
#   delay_seconds：抓取间隔，避免过快触发限流
#   attachment_exts：要下载的附件后缀，留空则不抓附件
SITE_CONFIGS = {
    "ipdbaike": {
        "base_url": "https://ipdbaike.com",
        "start_urls": [
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
        ],
        "allowed_domains": ["ipdbaike.com"],
        "use_jina": True,
        "article_pattern": r"\.html$",
        "max_depth": 3,
        "max_pages": 300,
        "delay_seconds": 1.0,
        "attachment_exts": (".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", ".zip", ".rar"),
    },
    # 禅道博客示例：直连抓取，走 Jina，深度 2
    "zentao_blog": {
        "base_url": "https://www.zentao.net",
        "start_urls": ["https://www.zentao.net/blog/"],
        "allowed_domains": ["zentao.net", "www.zentao.net"],
        "use_jina": True,
        "article_pattern": r"\.html$",
        "max_depth": 2,
        "max_pages": 150,
        "delay_seconds": 1.0,
        "attachment_exts": (".pdf", ".doc", ".docx", ".ppt", ".pptx"),
    },
    "pdma": {
        "base_url": "https://community.pdma.org",
        "start_urls": ["https://community.pdma.org/home"],
        "allowed_domains": ["community.pdma.org"],
        "use_jina": False,
        "article_pattern": r"/viewdocument|/blog/",
        "max_depth": 2,
        "max_pages": 120,
        "delay_seconds": 1.0,
        "attachment_exts": (".pdf", ".doc", ".docx", ".ppt", ".pptx"),
    },
    "six_sigma_daily": {
        "base_url": "https://www.sixsigmadaily.com",
        "start_urls": ["https://www.sixsigmadaily.com/"],
        "allowed_domains": ["sixsigmadaily.com", "www.sixsigmadaily.com"],
        "use_jina": False,  # 若页面访问正常，可考虑不使用 Jina 代理
        "article_pattern": r"/\d{4}/\d{2}/\d{2}/.+\.html$",
        # 例如 /2024/02/15/how-to-use-lean-six-sigma-for-better-time-management.html
        "max_depth": 2,
        "max_pages": 200,
        "delay_seconds": 1.0,
        "attachment_exts": (".pdf", ".ppt", ".pptx", ".xls", ".xlsx"),
    },
    "triz_journal": {
        "base_url": "https://the-trizjournal.com",
        "start_urls": ["https://the-trizjournal.com/"],
        "allowed_domains": ["the-trizjournal.com"],
        "use_jina": False,
        "article_pattern": r"/articles/.+\.html?$",  # 或者 /archives/ 或 /what-is-triz/ 等，需实际检测
        "max_depth": 2,
        "max_pages": 150,
        "delay_seconds": 1.0,
        "attachment_exts": (".pdf",),
    },
    "woshipm": {
        "base_url": "https://www.woshipm.com",
        "start_urls": ["https://www.woshipm.com/"],
        "allowed_domains": ["woshipm.com", "www.woshipm.com"],
        "use_jina": False,
        "article_pattern": r"/p/\d+\.html$",  # 如 /p/5360207.html
        "max_depth": 3,
        "max_pages": 300,
        "delay_seconds": 1.0,
        "attachment_exts": (".pdf", ".pptx",),
    },
    "huawei_corporate": {
        "base_url": "https://www.huawei.com",
        "start_urls": [
            "https://www.huawei.com/cn/corporate-information", # 公司简介
            "https://www.huawei.com/cn/corporate-governance", # 公司治理
            "https://www.huawei.com/cn/executives", # 管理层信息
            "https://www.huawei.com/cn/publications",# 华为出版
        ],
        "allowed_domains": ["huawei.com", "www.huawei.com"],
        "use_jina": True,
        "article_pattern": r"/en/(about-huawei|corporate-information|media-center/company-facts).*$",
        "max_depth": 2,
        "max_pages": 100,
        "delay_seconds": 1.0,
        "attachment_exts": (".pdf", ".docx", ".xlsx")
    },
}

# 默认站点键（运行时可用 --site 覆盖）
DEFAULT_SITE = "huawei_corporate"


def get_output_dirs(site_key: str):
    """
    按站点返回输出目录（文章 / 附件），形如 output/<site>_output/...
    """
    base = OUTPUT_ROOT / f"{site_key}_output"
    articles = base / "articles"
    attachments = base / "attachments"
    return articles, attachments

ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_ROOT = ROOT_DIR / "output"
LOG_DIR = ROOT_DIR / "logs"
LOG_FILE = LOG_DIR / "crawler.log"
