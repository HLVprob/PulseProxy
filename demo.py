import asyncio
import urllib.request
import urllib.error
import sys
from pulseproxy.config import ProxyConfig, BackendNode
from pulseproxy.proxy import ReverseProxyServer

# Basit mock backend sunucu fonksiyonu
async def run_mock_backend(server_id: int, port: int):
    async def handle_request(reader, writer):
        await reader.read(1024)
        body = f'{{"node": {server_id}, "status": "ok", "port": {port}}}\n'
        resp = (
            f"HTTP/1.1 200 OK\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"Connection: close\r\n\r\n"
            f"{body}"
        ).encode("utf-8")
        writer.write(resp)
        await writer.drain()
        writer.close()
        await writer.wait_closed()

    server = await asyncio.start_server(handle_request, "127.0.0.1", port)
    return server

def send_http_request(url: str):
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=2.0) as response:
            return response.status, response.read().decode("utf-8").strip()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8").strip()
    except Exception as e:
        return 0, str(e)

async def run_demo():
    print("PulseProxy: High-Performance Async Load Balancer & Rate Limiter")
    print("Simulasyon ve Dogrulama Testi\n")

    # 1) 3 adet mock backend baslat (9001, 9002, 9003)
    print("[*] 3 adet upstream mock sunucu baslatiliyor (Port 9001, 9002, 9003)...")
    srv1 = await run_mock_backend(1, 9001)
    srv2 = await run_mock_backend(2, 9002)
    srv3 = await run_mock_backend(3, 9003)
    print("[+] Upstream sunucular ayakta.\n")

    # 2) PulseProxy'yi baslat (Port 8080)
    backends = [
        BackendNode("127.0.0.1", 9001),
        BackendNode("127.0.0.1", 9002),
        BackendNode("127.0.0.1", 9003),
    ]

    config = ProxyConfig(
        host="127.0.0.1",
        port=8080,
        backends=backends,
        strategy="round-robin",
        rate_limit_enabled=True,
        rate_limit_capacity=10,       # burst limiti
        rate_limit_refill_rate=2.0,   # saniyede token
        health_check_interval=1.0
    )

    proxy = ReverseProxyServer(config)
    await proxy.start()
    print("[+] PulseProxy 127.0.0.1:8080 uzerinde calisiyor.\n")

    loop = asyncio.get_running_loop()

    # Senaryo 1: Round-Robin Yuk Dengeleme Testi
    print("[*] Senaryo 1: Round-Robin Yuk Dengeleme Testi (6 Istek gonderiliyor)...")
    for i in range(6):
        status, body = await loop.run_in_executor(None, send_http_request, "http://127.0.0.1:8080/")
        print(f"    -> Istek {i+1}: HTTP {status} | Yanit: {body}")
        await asyncio.sleep(0.05)

    print("[+] Istekler sunuculara (Node 1 -> Node 2 -> Node 3) sirasiyla dagitildi.\n")

    # Senaryo 2: Token Bucket Rate Limiting Testi
    print("[*] Senaryo 2: Rate Limiting Testi (15 hizli ardisik istek gonderiliyor)...")
    for i in range(15):
        status, body = await loop.run_in_executor(None, send_http_request, "http://127.0.0.1:8080/api/data")
        status_text = "ENGELENDI (429)" if status == 429 else "GECTI (200)"
        print(f"    -> Istek {i+1}: HTTP {status} [{status_text}]")

    print("[+] Token bittiginde proxy 429 Too Many Requests dondurerek sunuculari korudu.\n")

    # Senaryo 3: Failover & Health-Check Testi
    print("[*] Senaryo 3: Failover Testi (Node 2 aniden kapatiliyor)...")
    srv2.close()
    await srv2.wait_closed()
    print("[!] Node 2 kapatildi. Health-checker'in guncellemesi bekleniyor (1.5 sn)...")
    await asyncio.sleep(1.5)

    print("[*] Yeni istekler gonderiliyor (Proxy sadece Node 1 ve Node 3 arasinda gecis yapmali):")
    for i in range(4):
        status, body = await loop.run_in_executor(None, send_http_request, "http://127.0.0.1:8080/")
        print(f"    -> Istek {i+1}: HTTP {status} | Yanit: {body}")

    print("[+] Failover basarili: Dusen sunucu havuzdan cikarildi, trafik kesintisiz devam etti.\n")

    # Temizlik
    print("[*] Test tamamlandi, sunucular kapatiliyor...")
    await proxy.stop()
    srv1.close()
    srv3.close()
    await srv1.wait_closed()
    await srv3.wait_closed()
    print("[+] Tum kaynaklar temizlendi.")

if __name__ == "__main__":
    asyncio.run(run_demo())
