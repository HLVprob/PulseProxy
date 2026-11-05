import asyncio
import logging
from typing import Tuple
from .config import ProxyConfig, BackendNode
from .balancer import RoundRobinBalancer, LeastConnectionsBalancer
from .limiter import RateLimiter
from .health import HealthChecker

logger = logging.getLogger("PulseProxy.Core")

class ReverseProxyServer:
    def __init__(self, config: ProxyConfig):
        self.config = config
        self.limiter = RateLimiter(
            capacity=config.rate_limit_capacity,
            refill_rate=config.rate_limit_refill_rate
        )

        if config.strategy == "least-connections":
            self.balancer = LeastConnectionsBalancer(config.backends)
        else:
            self.balancer = RoundRobinBalancer(config.backends)

        self.health_checker = HealthChecker(
            backends=config.backends,
            interval=config.health_check_interval
        )
        self.server = None

    async def _read_http_headers(self, reader: asyncio.StreamReader) -> Tuple[bytes, dict]:
        header_data = b""
        while b"\r\n\r\n" not in header_data:
            chunk = await reader.read(1024)
            if not chunk:
                break
            header_data += chunk

        if not header_data:
            return b"", {}

        parts = header_data.split(b"\r\n\r\n", 1)
        headers_raw = parts[0]
        remaining_body = parts[1] if len(parts) > 1 else b""

        # header satirlarini ayrıştır
        lines = headers_raw.decode("latin1", errors="replace").split("\r\n")
        request_line = lines[0] if lines else ""

        headers = {"_request_line": request_line}
        for line in lines[1:]:
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip().lower()] = v.strip()

        return header_data, headers

    async def _handle_client(self, client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter):
        client_addr = client_writer.get_extra_info("peername")
        client_ip = client_addr[0] if client_addr else "127.0.0.1"

        # 1) Rate Limit kontrolu
        if self.config.rate_limit_enabled:
            allowed = await self.limiter.is_allowed(client_ip)
            if not allowed:
                response = (
                    b"HTTP/1.1 429 Too Many Requests\r\n"
                    b"Content-Type: text/plain\r\n"
                    b"Retry-After: 1\r\n"
                    b"Connection: close\r\n\r\n"
                    b"Rate limit exceeded. Please slow down.\r\n"
                )
                client_writer.write(response)
                await client_writer.drain()
                client_writer.close()
                await client_writer.wait_closed()
                return

        # 2) Header oku
        try:
            raw_request, headers = await asyncio.wait_for(
                self._read_http_headers(client_reader),
                timeout=self.config.connection_timeout
            )
        except Exception:
            client_writer.close()
            return

        if not raw_request:
            client_writer.close()
            return

        # 3) Backend sec
        backend = await self.balancer.get_next()
        if not backend:
            response = (
                b"HTTP/1.1 503 Service Unavailable\r\n"
                b"Content-Type: text/plain\r\n"
                b"Connection: close\r\n\r\n"
                b"All backend servers are down.\r\n"
            )
            client_writer.write(response)
            await client_writer.drain()
            client_writer.close()
            return

        # 4) Proxy headerlarini ekle ve ilet
        backend.active_connections += 1
        try:
            backend_reader, backend_writer = await asyncio.wait_for(
                asyncio.open_connection(backend.host, backend.port),
                timeout=self.config.connection_timeout
            )

            # X-Forwarded header ekle
            req_parts = raw_request.split(b"\r\n\r\n", 1)
            head_part = req_parts[0]
            body_part = req_parts[1] if len(req_parts) > 1 else b""

            proxy_headers = f"\r\nX-Forwarded-For: {client_ip}\r\nX-Proxy: PulseProxy-1.0\r\n\r\n".encode("latin1")
            modified_request = head_part + proxy_headers + body_part

            backend_writer.write(modified_request)
            await backend_writer.drain()

            # backend yanitini alip client'a ilet
            while True:
                chunk = await backend_reader.read(4096)
                if not chunk:
                    break
                client_writer.write(chunk)
                await client_writer.drain()

            backend_writer.close()
            await backend_writer.wait_closed()

        except Exception as e:
            logger.error(f"Backend aktarim hatasi ({backend.address}): {e}")
            err_resp = (
                b"HTTP/1.1 502 Bad Gateway\r\n"
                b"Content-Type: text/plain\r\n"
                b"Connection: close\r\n\r\n"
                b"Failed to reach upstream backend.\r\n"
            )
            try:
                client_writer.write(err_resp)
                await client_writer.drain()
            except Exception:
                pass
        finally:
            backend.active_connections = max(0, backend.active_connections - 1)
            try:
                client_writer.close()
                await client_writer.wait_closed()
            except Exception:
                pass

    async def start(self):
        self.health_checker.start()
        self.server = await asyncio.start_server(
            self._handle_client,
            self.config.host,
            self.config.port
        )
        logger.info(f"[*] PulseProxy dinliyor: http://{self.config.host}:{self.config.port}")
        logger.info(f"[*] Strateji: {self.config.strategy}")
        for b in self.config.backends:
            logger.info(f"    -> Upstream: {b.address}")

    async def stop(self):
        self.health_checker.stop()
        if self.server:
            self.server.close()
            await self.server.wait_closed()
