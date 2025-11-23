import logging
from pathlib import Path
from typing import Optional

import requests

from .config import HEADERS


def _safe_title(title: str) -> str:
    # 仅保留字母、数字、空格、下划线和中划线，其他字符替换为下划线
    return "".join(c if (c.isalnum() or c in (" ", "_", "-")) else "_" for c in title).strip()


def save_markdown_article(url: str, title: str, content: str, output_dir: Path) -> Path:
    """
    保存文章为 markdown 文件。
    - 文件名基于安全化标题（只留字母数字/空格/下划线/中划线）。
    - output_dir 由站点配置决定，互不干扰。
    """
    output_dir.mkdir(parents=True, exist_ok=True)  # 确保目录存在
    safe_title = _safe_title(title) or "untitled"  # 若标题为空，用默认名
    filepath = output_dir / f"{safe_title}.md"  # 生成文件路径
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\nURL: {url}\n\n{content}")  # 写入标题、URL 和正文
    logging.info("Article saved: %s", filepath)
    return filepath  # 返回保存路径


def save_attachment(file_url: str, output_dir: Path, referer: Optional[str] = None) -> Optional[Path]:
    """
    下载附件到指定目录，透传 Referer 以兼容防盗链。失败会清理不完整文件。
    - output_dir：当前站点的附件目录。
    - referer：来源页 URL，部分站点需要。
    """
    output_dir.mkdir(parents=True, exist_ok=True)  # 确保目录存在
    local_name = file_url.split("/")[-1] or "attachment.bin"  # 从 URL 取文件名
    filepath = output_dir / local_name  # 目标文件路径
    if filepath.exists():  # 已存在则跳过
        logging.info("Attachment already exists, skip: %s", filepath)
        return filepath

    # Some endpoints enforce Referer anti-leech; send page URL when available.
    headers = dict(HEADERS)  # 复制 headers，避免污染全局
    headers["Referer"] = referer or headers.get("Referer", "")  # 设置或保留 Referer

    try:
        with requests.get(file_url, headers=headers, stream=True, timeout=30) as resp:  # 流式下载
            resp.raise_for_status()  # 检查状态码
            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):  # 分块写入
                    if chunk:
                        f.write(chunk)
        logging.info("Attachment saved: %s", filepath)
        return filepath  # 成功返回路径
    except requests.RequestException as exc:
        logging.error("Failed to download attachment %s -> %s", file_url, exc)
        if filepath.exists():  # 出错时清理残留文件
            try:
                filepath.unlink()
            except OSError:
                pass
        return None  # 失败返回 None
