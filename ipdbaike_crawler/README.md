# ipdbaike_crawler

Modular crawler for https://ipdbaike.com using Jina Reader as the primary fetch path to avoid 403, with a breadth-first queue and attachment downloading.

## Structure
```
ipdbaike_crawler/
├── crawler/
│   ├── __init__.py
│   ├── config.py          # 配置：入口 URL、Headers、延迟、输出目录、深度等
│   ├── fetcher.py         # 抓取：Jina 优先，失败回落直连
│   ├── parser.py          # 解析：链接抽取、文章/列表判断、附件链接抽取
│   ├── storage.py         # 存储：Markdown 保存、附件下载
│   ├── queue_manager.py   # 队列：待抓/已抓管理
│   └── main.py            # 入口：初始化日志、启动 BFS 抓取
├── output/
│   ├── articles/          # 抓到的文章（Markdown）
│   └── attachments/       # 附件文件
├── logs/
│   └── crawler.log
└── README.md
```

## Quick start
1) 安装依赖（已存在 requests / beautifulsoup4 则可跳过）：
```bash
pip install requests beautifulsoup4
```
2)（如需 Playwright 抓微信公众号验证码）安装：
```bash
pip install playwright
python -m playwright install chromium
```
3) 运行（在仓库根目录）：
```bash
# 默认爬 ipdbaike
python -m crawler.main
# 爬其他站点（示例 zentao 博客 / pdma 社区）
python -m crawler.main --site zentao_blog
python -m crawler.main --site pdma
```
4) 输出：
- 文章保存在 `output/<site>_output/articles/`，Markdown 文件包含源 URL。
- 附件保存在 `output/<site>_output/attachments/`。
- 日志写到 `logs/crawler.log` 并同步输出到控制台。

## 配置说明
- `config.py`
  - `START_URLS`: 一级入口列表（默认包含首页 + 全部一级分类）。
  - `MAX_DEPTH`: 默认 3（入口=0，分类=1，分页/列表=2，文章=3）。
  - `MAX_PAGES`: 全局抓取上限，防止跑太久。可按需加大或设为很大值。
  - `DELAY_SECONDS`: 抓取间隔，避免过快触发限流。
  - `ATTACHMENT_EXTS`: 需要下载的附件扩展名白名单。
- 路径：输出目录、日志目录可在此调整。

### 扩展新站点
在 `crawler/config.py` 的 `SITE_CONFIGS` 中新增条目，配置 `base_url`、`start_urls`、`allowed_domains`、`article_pattern`、`attachment_exts`、`max_depth`、`max_pages`、`delay_seconds`，即可通过 `--site your_key` 启动。

## 运行策略
- **优先 Jina**：`fetch_via_jina` 先取 markdown，失败再直连抓 html。
- **链接抽取**：markdown 用正则抽取站内链接；html 用 BeautifulSoup 抽取 `<a href>`，并归一化/去重/过滤静态资源。
- **队列去重**：`CrawlQueue` 记录已访问 URL，避免重复抓取。
- **附件下载**：正文中出现的 `pdf/doc/ppt/xls/zip/rar` 链接会尝试下载到 `output/attachments/`。
- **安全阈值**：`MAX_PAGES` 避免跑太久；日志记录抓取编号、深度、URL、错误信息。

## 调优建议
- 小范围测试：先将 `START_URLS` 缩到单个分类、`MAX_DEPTH=2`、`MAX_PAGES=50` 试跑。
- 全站抓取：确认稳定后再调大 `MAX_PAGES`、`MAX_DEPTH`，并酌情增大 `DELAY_SECONDS`。
- 代理/网络：如直连经常 403，可保持 Jina 优先；如 Jina 偶尔超时，可在 `fetcher.py` 调整超时时间或重试逻辑。
- 错误恢复：日志里查失败的 URL，可再次手动加入 `START_URLS` 重跑。

## 可能待办
- 增加重试/失败队列。
- 提取 html 里的图片/媒体另存。
- 将抓取结果以 JSON/CSV 索引输出，便于后续分析。
