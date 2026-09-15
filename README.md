# SmartDNS & Gaming Proxy Infrastructure

A carrier-grade, low-latency SmartDNS and transparent SNI tunneling system engineered for console gamers (PlayStation 5, PlayStation 4, Xbox Series X/S, Nintendo Switch, and PC) in restricted network environments.

---

## Architecture Overview

```
Console (PS5/Xbox) 
    │
    │ [DNS Query (UDP/TCP: 53)]
    ▼
Iran Edge Node (CoreDNS)
    ├─► Normal / CDN Domains (e.g. game downloads) ──► Direct Native Resolution (Max Line Speed)
    └─► Geo-Restricted Game Domains (auth, lobbies)  ──► Resolves to Iran Node IP
                                                           │
                                                           ▼
                                            Iran SNI Proxy (HAProxy / ssl_preread)
                                                           │
                                                           │ [Loss-Resistant Tunnel]
                                                           ▼
                                            Germany Egress Gateway (Rathole)
                                                           │
                                                           ▼
                                            Game Servers (PSN, Xbox Live, EA, Epic)
```

---

## Quick Start Deployment

### 1. Germany Server (Run First)
On your German/European server (Ubuntu/Debian):

```bash
# Clone or upload repository
cd DNS
chmod +x scripts/*.sh

# Run Germany Egress setup
sudo ./scripts/deploy.sh --role germany --token "YOUR_SUPER_SECRET_TOKEN"
```

### 2. Iran Server (Run Second)
On your Iranian server (Ubuntu/Debian):

```bash
# Clone or upload repository
cd DNS
chmod +x scripts/*.sh

# Run Iran Edge setup
sudo ./scripts/deploy.sh --role iran \
  --iran-ip "IRAN_SERVER_PUBLIC_IP" \
  --germany-ip "GERMANY_SERVER_PUBLIC_IP" \
  --token "YOUR_SUPER_SECRET_TOKEN"
```

---

## Verification & Diagnostic Testing

To verify DNS query response times, split-horizon overrides, and end-to-end TLS SNI connectivity:

```bash
bash scripts/benchmark.sh IRAN_SERVER_PUBLIC_IP
```

---

## File Structure

- `dns/gaming-domains.txt`: Curated domain list for PlayStation, Xbox, EA, Activision, Battle.net, Epic Games, Riot, Nintendo, and Discord.
- `dns/Corefile.template`: High-performance CoreDNS configuration with cache prefetching and query rate limiting.
- `proxy/haproxy.cfg.template`: Zero-decrypt SNI pass-through proxy configuration.
- `tunnel/`: Low-overhead, multiplexed transport configurations (Rathole).
- `scripts/deploy.sh`: Automated deployment script for both roles.
- `scripts/benchmark.sh`: Latency, packet loss, and TLS handshake diagnostic suite.
