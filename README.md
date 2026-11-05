# PulseProxy

[![Language](https://img.shields.io/badge/Python_3.10+-3776AB?logo=python&logoColor=white)](#)
[![Platform](https://img.shields.io/badge/Cross--Platform-0078D6?logo=linux&logoColor=white)](#)
[![Architecture](https://img.shields.io/badge/Asyncio-Core-orange)](#)
[![License](https://img.shields.io/badge/MIT-green)](#)

Python'un standart `asyncio` kütüphanesi üzerine sıfırdan inşa edilmiş, harici hiçbir bağımlılığı (pip paketi) bulunmayan yüksek performanslı asenkron reverse proxy, yük dengeleyici (load balancer) ve rate limiter.

Mikroservisler ve web sunucuları arasında gelen HTTP/1.1 trafiğini dağıtır, sunucu sağlığını arka planda sürekli kontrol eder ve Token Bucket algoritmasıyla istemci bazlı hız sınırlaması uygular.

## Özellikler

* **Yük Dengeleme Stratejileri:** Round-Robin ve Least-Connections (en az aktif bağlantıya sahip sunucuyu seçme).
* **Token Bucket Rate Limiting:** IP tabanlı token kovası algoritması. Ani istek patlamalarını (burst) tolere eder, sınırı aşan isteklere `HTTP 429 Too Many Requests` döndürür.
* **Periyodik Health-Check:** Arka planda upstream sunucuları düzenli aralıklarla yoklar. Düşen sunucuyu havuzdan otomatik çıkarır, toparlandığında trafiği tekrar açar.
* **Sıfır Bağımlılık (Zero Dependencies):** Sadece Python standart kütüphanesini (`asyncio`, `dataclasses`, `time`, `urllib`) kullanır. `pip install` gerektirmez, klonlayıp anında çalıştırılabilir.
* **Header Yönetimi:** `X-Forwarded-For`, `X-Forwarded-Host` ve `Via` proxy başlıklarını otomatik enjekte eder.

## Strateji Karşılaştırması

| Özellik | Round-Robin | Least-Connections |
| :--- | :--- | :--- |
| **Yönlendirme Mantığı** | Sırayla bir sonraki sunucuya aktarır | Aktif bağlantı sayısı en az olana aktarır |
| **Kullanım Senaryosu** | Eşit donanımlı ve benzer işlem süreleri | Uzun süren istekler / değişken iş yükleri |
| **Failover Desteği** | Sağlıklı sunuculara otomatik atlar | Sağlıklı sunuculara otomatik atlar |

## Dosya Yapısı

* `pulseproxy/config.py` - Proxy ve backend sunucu konfigürasyon veri sınıfları.
* `pulseproxy/balancer.py` - Round-Robin ve Least-Connections yük dengeleme algoritmaları.
* `pulseproxy/limiter.py` - Asenkron Token Bucket rate limiter motoru.
* `pulseproxy/health.py` - Arka plan aktif sunucu sağlık kontrolcüsü.
* `pulseproxy/proxy.py` - İstemci ve backend arası akış yönlendirici (Core streaming server).
* `main.py` - CLI başlatıcısı.
* `demo.py` - 3 mock sunucu kaldırıp test senaryolarını çalıştıran simülasyon aracı.

## Hızlı Başlangıç

### 1. Simülasyonu Çalıştırma (Demo)
Sistemde hazır 3 adet mock sunucu ayağa kaldırır, yük dengelemeyi, rate limiting'i ve sunucu çökme (failover) senaryolarını test eder:

```bash
python demo.py
```

### 2. Kendi Sunucularınızla Başlatma
```bash
python main.py --host 127.0.0.1 --port 8080 --backends 127.0.0.1:9001 127.0.0.1:9002 --strategy round-robin
```

## Örnek Çıktı

```text
PulseProxy: High-Performance Async Load Balancer & Rate Limiter
Simulasyon ve Dogrulama Testi

[*] 3 adet upstream mock sunucu baslatiliyor (Port 9001, 9002, 9003)...
[+] Upstream sunucular ayakta.

[+] PulseProxy 127.0.0.1:8080 uzerinde calisiyor.

[*] Senaryo 1: Round-Robin Yuk Dengeleme Testi (6 Istek gonderiliyor)...
    -> Istek 1: HTTP 200 | Yanit: {"node": 1, "status": "ok", "port": 9001}
    -> Istek 2: HTTP 200 | Yanit: {"node": 2, "status": "ok", "port": 9002}
    -> Istek 3: HTTP 200 | Yanit: {"node": 3, "status": "ok", "port": 9003}
    -> Istek 4: HTTP 200 | Yanit: {"node": 1, "status": "ok", "port": 9001}
    -> Istek 5: HTTP 200 | Yanit: {"node": 2, "status": "ok", "port": 9002}
    -> Istek 6: HTTP 200 | Yanit: {"node": 3, "status": "ok", "port": 9003}
[+] Istekler sunuculara (Node 1 -> Node 2 -> Node 3) sirasiyla dagitildi.

[*] Senaryo 2: Rate Limiting Testi (15 hizli ardisik istek gonderiliyor)...
    -> Istek 1: HTTP 200 [GECTI (200)]
    -> Istek 2: HTTP 200 [GECTI (200)]
    -> Istek 3: HTTP 200 [GECTI (200)]
    -> Istek 4: HTTP 200 [GECTI (200)]
    -> Istek 5: HTTP 429 [ENGELENDI (429)]
[+] Token bittiginde proxy 429 Too Many Requests dondurerek sunuculari korudu.

[*] Senaryo 3: Failover Testi (Node 2 aniden kapatiliyor)...
[!] Node 2 kapatildi. Health-checker'in guncellemesi bekleniyor (1.5 sn)...
[*] Yeni istekler gonderiliyor (Proxy sadece Node 1 ve Node 3 arasinda gecis yapmali):
    -> Istek 1: HTTP 200 | Yanit: {"node": 1, "status": "ok", "port": 9001}
    -> Istek 2: HTTP 200 | Yanit: {"node": 3, "status": "ok", "port": 9003}
[+] Failover basarili: Dusen sunucu havuzdan cikarildi, trafik kesintisiz devam etti.

[+] Tum kaynaklar temizlendi.
```

## Lisans
MIT
