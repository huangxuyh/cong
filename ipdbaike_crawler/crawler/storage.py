import logging
from pathlib import Path
from typing import Optional

import requests

from .config import HEADERS


def _safe_title(title: str) -> str:
    return "".join(c if (c.isalnum() or c in (" ", "_", "-")) else "_" for c in title).strip()


def save_markdown_article(url: str, title: str, content: str, output_dir: Path) -> Path:
    """保存文章为 markdown 文件，文件名基于安全化标题。"""
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_title = _safe_title(title) or "untitled"
    filepath = output_dir / f"{safe_title}.md"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\nURL: {url}\n\n{content}")
    logging.info("Article saved: %s", filepath)
    return filepath


def save_attachment(file_url: str, output_dir: Path, referer: Optional[str] = None) -> Optional[Path]:
    """
    下载附件到指定目录，透传 Referer 以兼容防盗链。失败会清理不完整文件。
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    local_name = file_url.split("/")[-1] or "attachment.bin"
    filepath = output_dir / local_name
    if filepath.exists():
        logging.info("Attachment already exists, skip: %s", filepath)
        return filepath

    # Some endpoints enforce Referer anti-leech; send page URL when available.
    headers = dict(HEADERS)
    headers["Referer"] = referer or headers.get("Referer", "")

    try:
        with requests.get(file_url, headers=headers, stream=True, timeout=30) as resp:
            resp.raise_for_status()
            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        logging.info("Attachment saved: %s", filepath)
        return filepath
    except requests.RequestException as exc:
        logging.error("Failed to download attachment %s -> %s", file_url, exc)
        if filepath.exists():
            try:
                filepath.unlink()
            except OSError:
                pass
        return None
