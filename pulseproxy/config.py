from dataclasses import dataclass, field
from typing import List

@dataclass
class BackendNode:
    host: str
    port: int
    weight: int = 1
    is_alive: bool = True
    active_connections: int = 0
    failure_count: int = 0

    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"

@dataclass
class ProxyConfig:
    host: str = "127.0.0.1"
    port: int = 8080
    backends: List[BackendNode] = field(default_factory=list)
    strategy: str = "round-robin"  # round-robin veya least-connections
    rate_limit_enabled: bool = True
    rate_limit_capacity: int = 10   # burst token limiti
    rate_limit_refill_rate: float = 2.0  # saniyede yenilenen token
    health_check_interval: float = 3.0  # saniye
    connection_timeout: float = 5.0
