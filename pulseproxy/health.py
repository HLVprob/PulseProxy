import asyncio
import logging
from typing import List
from .config import BackendNode

logger = logging.getLogger("PulseProxy.Health")

class HealthChecker:
    def __init__(self, backends: List[BackendNode], interval: float = 3.0, timeout: float = 2.0):
        self.backends = backends
        self.interval = interval
        self.timeout = timeout
        self.is_running = False
        self._task: asyncio.Task = None

    async def check_node(self, node: BackendNode) -> bool:
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(node.host, node.port),
                timeout=self.timeout
            )
            writer.close()
            await writer.wait_closed()
            return True
        except Exception:
            return False

    async def _run_loop(self):
        while self.is_running:
            for node in self.backends:
                alive = await self.check_node(node)
                if alive != node.is_alive:
                    node.is_alive = alive
                    status_str = "AYAKTA" if alive else "DUSTU"
                    logger.info(f"[Health] Sunucu {node.address} durumu degisti: {status_str}")

            await asyncio.sleep(self.interval)

    def start(self):
        if not self.is_running:
            self.is_running = True
            self._task = asyncio.create_task(self._run_loop())

    def stop(self):
        if self.is_running:
            self.is_running = False
            if self._task:
                self._task.cancel()
