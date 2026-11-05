import time
import asyncio
from typing import Dict

class TokenBucket:
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = float(capacity)
        self.tokens = float(capacity)
        self.refill_rate = float(refill_rate)
        self.last_update = time.monotonic()
        self.lock = asyncio.Lock()

    async def consume(self, count: float = 1.0) -> bool:
        async with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.last_update = now

            # gecen sureye gore token ekle
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)

            if self.tokens >= count:
                self.tokens -= count
                return True
            return False

class RateLimiter:
    def __init__(self, capacity: int = 10, refill_rate: float = 2.0):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.buckets: Dict[str, TokenBucket] = {}
        self.lock = asyncio.Lock()

    async def is_allowed(self, client_ip: str) -> bool:
        async with self.lock:
            if client_ip not in self.buckets:
                self.buckets[client_ip] = TokenBucket(self.capacity, self.refill_rate)
            bucket = self.buckets[client_ip]

        return await bucket.consume(1.0)
