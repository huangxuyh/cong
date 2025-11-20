import logging
from typing import Optional

import requests

from .config import HEADERS, JINA_PREFIX


def fetch_via_jina(url: str) -> Optional[str]:
    """Fetch page content via Jina Reader; returns markdown text or None."""
    jina_url = JINA_PREFIX + url
    try:
        resp = requests.get(jina_url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        logging.info("Jina fetch succeeded: %s", url)
        return resp.text
    except requests.RequestException as exc:
        logging.warning("Jina fetch failed: %s -> %s", url, exc)
        return None


def fetch_direct(url: str) -> Optional[str]:
    """Fetch page directly from origin; returns HTML text or None."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding
        logging.info("Direct fetch succeeded: %s", url)
        return resp.text
    except requests.RequestException as exc:
        logging.error("Direct fetch failed: %s -> %s", url, exc)
        return None
