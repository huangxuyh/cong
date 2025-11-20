from pathlib import Path

# Base settings
BASE_URL = "https://ipdbaike.com"
JINA_PREFIX = "https://r.jina.ai/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": BASE_URL + "/",
}

# Entry URLs (level 0)
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

# Limits and paths
MAX_DEPTH = 3  # 0=home, 1=category, 2=list/pagination, 3=articles
MAX_PAGES = 300  # global safety cap
DELAY_SECONDS = 1.0

ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_ARTICLE_DIR = ROOT_DIR / "output" / "articles"
OUTPUT_ATTACHMENT_DIR = ROOT_DIR / "output" / "attachments"
LOG_DIR = ROOT_DIR / "logs"
LOG_FILE = LOG_DIR / "crawler.log"

# Attachment extensions to download
ATTACHMENT_EXTS = (".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", ".zip", ".rar")

# Regex patterns
ARTICLE_PATTERN = r"\.html$"
ATTACHMENT_PATTERN = r"https?://ipdbaike\.com/[^\s\"']+(?:%s)" % "|".join(ATTACHMENT_EXTS)
