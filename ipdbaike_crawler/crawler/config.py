from pathlib import Path

# 全局头部与 Jina 前缀配置（Jina 用于绕过部分站点的 403）
JINA_PREFIX = "https://r.jina.ai/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

# 站点配置：可按模板新增其他站点
# 字段说明：
#   base_url：站点基准 URL
#   start_urls：入口列表
#   allowed_domains：允许的域名（过滤外链）
#   use_jina：是否优先走 Jina 代理
#   article_pattern：文章页正则
#   max_depth/max_pages/delay_seconds：爬取控制
#   attachment_exts：需要下载的附件后缀
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
    "zentao_blog": {
        "base_url": "https://www.zentao.net",
        "start_urls": ["https://www.zentao.net/blog/"],
        "allowed_domains": ["zentao.net", "www.zentao.net"],
        "use_jina": False,
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
}

# 默认站点键（运行时可用 --site 覆盖）
DEFAULT_SITE = "zentao_blog"


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
