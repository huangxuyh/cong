from collections import deque
from typing import Deque, Optional, Set, Tuple


class CrawlQueue:
    """
    简单的 BFS 队列：
    - 维护待抓取的 (url, depth) 队列，先进先出。
    - 维护已访问集合，防止重复抓取/循环。
    - 提供入队、出队、标记、长度等基础操作。
    """

    def __init__(self) -> None:
        # queue: FIFO 队列，存储 (url, depth)
        self.queue: Deque[Tuple[str, int]] = deque()
        # visited: 已抓或正在处理的 URL 集合，避免重复
        self.visited: Set[str] = set()

    def add(self, url: str, depth: int) -> None:
        """
        入队一个 URL。
        - 忽略空 URL
        - 若已访问则直接返回
        """
        if not url:
            return
        if url in self.visited:
            return
        self.queue.append((url, depth))

    def pop(self) -> Optional[Tuple[str, int]]:
        """出队一个 (url, depth)。若队列空，返回 None。"""
        return self.queue.popleft() if self.queue else None

    def mark_visited(self, url: str) -> None:
        """标记 URL 已访问，避免重复抓取。"""
        self.visited.add(url)

    def __len__(self) -> int:
        """获取当前待抓队列长度。"""
        return len(self.queue)
