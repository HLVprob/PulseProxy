import asyncio
from typing import List, Optional
from .config import BackendNode

class BaseBalancer:
    def __init__(self, backends: List[BackendNode]):
        self.backends = backends
        self.lock = asyncio.Lock()

    async def get_next(self) -> Optional[BackendNode]:
        raise NotImplementedError

class RoundRobinBalancer(BaseBalancer):
    def __init__(self, backends: List[BackendNode]):
        super().__init__(backends)
        self.index = 0

    async def get_next(self) -> Optional[BackendNode]:
        async with self.lock:
            healthy_nodes = [node for node in self.backends if node.is_alive]
            if not healthy_nodes:
                return None

            selected = healthy_nodes[self.index % len(healthy_nodes)]
            self.index = (self.index + 1) % len(healthy_nodes)
            return selected

class LeastConnectionsBalancer(BaseBalancer):
    async def get_next(self) -> Optional[BackendNode]:
        async with self.lock:
            healthy_nodes = [node for node in self.backends if node.is_alive]
            if not healthy_nodes:
                return None

            # aktif baglanti sayisi en az olan sunucuyu sec
            selected = min(healthy_nodes, key=lambda node: node.active_connections)
            return selected
