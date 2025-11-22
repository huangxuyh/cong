from collections import deque
from typing import Deque, Optional, Set, Tuple


class CrawlQueue:
    """简单的 BFS 队列，记录已访问，避免重复抓取。"""
    def __init__(self) -> None:
        self.queue: Deque[Tuple[str, int]] = deque()
        self.visited: Set[str] = set()

    def add(self, url: str, depth: int) -> None:
        if not url:
            return
        if url in self.visited:
            return
        self.queue.append((url, depth))

    def pop(self) -> Optional[Tuple[str, int]]:
        return self.queue.popleft() if self.queue else None

    def mark_visited(self, url: str) -> None:
        self.visited.add(url)

    def __len__(self) -> int:  # for convenience
        return len(self.queue)
