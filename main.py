import asyncio
import logging
import argparse
import sys
from pulseproxy.config import ProxyConfig, BackendNode
from pulseproxy.proxy import ReverseProxyServer

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    )

def parse_args():
    parser = argparse.ArgumentParser(description="PulseProxy: Asenkron Reverse Proxy & Load Balancer")
    parser.add_argument("--host", default="127.0.0.1", help="Proxy dinleme hostu")
    parser.add_argument("--port", type=int, default=8080, help="Proxy dinleme portu")
    parser.add_argument("--backends", nargs="+", default=["127.0.0.1:9001", "127.0.0.1:9002"], help="Upstream sunucular (host:port)")
    parser.add_argument("--strategy", choices=["round-robin", "least-connections"], default="round-robin", help="Yuk dengeleme algoritmasi")
    parser.add_argument("--rate-limit", type=int, default=10, help="IP basina maksimum istek (burst)")
    parser.add_argument("--refill-rate", type=float, default=2.0, help="Saniyede eklenen token sayisi")
    return parser.parse_args()

async def main():
    setup_logging()
    args = parse_args()

    backend_nodes = []
    for b in args.backends:
        parts = b.split(":")
        backend_nodes.append(BackendNode(host=parts[0], port=int(parts[1])))

    config = ProxyConfig(
        host=args.host,
        port=args.port,
        backends=backend_nodes,
        strategy=args.strategy,
        rate_limit_capacity=args.rate_limit,
        rate_limit_refill_rate=args.refill_rate
    )

    proxy = ReverseProxyServer(config)
    await proxy.start()

    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n[*] Kapatiliyor...")
        await proxy.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
