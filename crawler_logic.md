# 爬虫逻辑概要

本文汇总当前工程的爬虫逻辑，便于从整体到细节快速理解和扩展。

## 1. 配置驱动的多站点架构（小白向）
所有站点配置都在 `crawler/config.py` 的 `SITE_CONFIGS` 字典里，每个站点一个键：
- `base_url`：站点基准 URL，用来判断“是否本站链接”，也用于列表页判定。
- `start_urls`：入口 URL 列表，从这里开始 BFS（可以是首页、分类页等）。
- `allowed_domains`：允许的域名白名单，链接必须包含其中任意一个，否则丢弃（防止跑到外站）。
- `use_jina`：是否优先走 Jina 代理抓取（适合被 403/反爬的站点，例如 ipdbaike）。
- `article_pattern`：文章页的正则表达式，匹配成功则视为终点页进行保存；不再继续下钻。
- `max_depth`：最大抓取深度（入口=0，分类=1，列表=2，文章=3...）。超出则不再入队。
- `max_pages`：全局抓取页数上限，防止无限跑。
- `delay_seconds`：每抓完一页后的休眠秒数，避免请求过快触发限流。
- `attachment_exts`：需要下载的附件后缀列表（留空则不抓附件）。
- 输出路径：自动按站点隔离，`output/<site>_output/articles/` 和 `output/<site>_output/attachments/`。
- 默认站点：`DEFAULT_SITE`，命令行未指定 `--site` 时使用。

现有示例：
- `ipdbaike`：用 Jina，深度 3，文章用 `.html` 匹配，附件包含 pdf/doc/ppt/xls/zip/rar。
- `zentao_blog`：直连，深度 2，文章 `.html`，附件 pdf/doc/ppt。
- `pdma`：直连，深度 2，文章匹配 `/viewdocument|/blog/`，附件 pdf/doc/ppt。

### 如何新增一个站点（模板）
在 `SITE_CONFIGS` 里添加一项，例如：
```python
"my_site": {
    "base_url": "https://example.com",
    "start_urls": ["https://example.com/"],  # 可放多个入口
    "allowed_domains": ["example.com", "www.example.com"],
    "use_jina": False,                        # 被 403/反爬严重可改 True
    "article_pattern": r"\\.html$",           # 文章判定规则
    "max_depth": 2,                           # 入口=0，列表=1，文章=2
    "max_pages": 200,                         # 全局安全阈值
    "delay_seconds": 1.0,                     # 节流
    "attachment_exts": (".pdf", ".doc"),      # 需要下载的附件后缀
},
```
然后运行：
```bash
python -m crawler.main --site my_site
```

调参建议：
- 403 多：`use_jina=True`；必要时加大 `delay_seconds`。
- 列表层级深：调大 `max_depth`，并确认 `article_pattern` 不误判列表。
- 页数太多：先把 `max_pages` 设小做试跑，确认无误后再放大。
- 附件过多：缩小 `attachment_exts` 或留空跳过附件下载。

## 2. 抓取流程（`crawler/main.py`）
1) 读取站点配置，建立按站点的输出目录，初始化日志。
2) 使用 `CrawlQueue` 做 BFS：
   - 队列元素为 `(url, depth)`；`visited` 集合去重。
3) 出队后检查深度/已访问/总页数上限。
4) 抓取页面：
   - 若 `use_jina=True`，先调用 `fetch_via_jina`（Markdown）；失败回落 `fetch_direct`（HTML）。
5) 处理附件：`extract_attachment_links` 基于后缀匹配，`save_attachment` 透传 Referer，写入当前站点的附件目录。
6) 分支：
   - 文章页：匹配 `article_pattern`，标题取 Markdown 的 `Title:/# heading` 或 URL，`save_markdown_article`。
   - 列表页：从 Markdown 或 HTML 抽取站内链接（过滤域/附件/去重），按 `depth+1` 入队。
7) 循环至队列耗尽或达到 `max_pages`；全程按 `delay_seconds` 休眠节流。

## 3. 关键模块
- `fetcher.py`：`fetch_via_jina`（代理获取 Markdown）、`fetch_direct`（直连 HTML）。
- `parser.py`：
  - `normalize_url` 归一化并按 `allowed_domains` 过滤。
  - `looks_like_asset` 过滤静态资源/附件。
  - `extract_links_from_markdown/html` 过滤跨域/静态资源并去重。
  - `is_article_page`/`is_list_page` 基于正则与 base_url。
  - `extract_attachment_links` 按附件后缀匹配。
  - `pick_title_from_markdown` 抽取标题。
- `storage.py`：`save_markdown_article`（安全化标题，写 md）、`save_attachment`（Referer 透传，失败清理半成品）。
- `queue_manager.py`：BFS 队列与 visited 去重。
- `wechat_search.py`/`wechat_playwright.py`：微信文章抓取（搜狗 + Cookie 持久化），与主爬虫逻辑独立。

## 4. 扩展新站点的步骤
1) 在 `SITE_CONFIGS` 中添加新条目，设定 base_url、start_urls、allowed_domains、article_pattern、深度/页数/附件等。
2) 运行时指定：`python -m crawler.main --site your_key`。
3) 如需代理/特殊 UA，可在配置里调整 HEADERS 或 `use_jina`。

## 5. 输出与日志
- 文章：`output/<site>_output/articles/*.md`（含源 URL）。
- 附件：`output/<site>_output/attachments/`。
- 日志：`logs/crawler.log`（文件 + 控制台）。

## 6. 注意事项
- Jina 适合被 403 的站点，若代理失败会自动回落直连。
+- 合理调 `max_depth/max_pages/delay_seconds`，避免跑太久或触发限流。
-- 附件匹配仅按后缀/路径简单过滤，若需更严格可在配置或 parser 中细化规则。
