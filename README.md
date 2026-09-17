<div align="center">

# 🎮 SmartDNS & Anti-Sanction Gaming Gateway
### Distributed Carrier-Grade SmartDNS & Transparent SNI Routing Platform

[![Platform](https://img.shields.io/badge/Platform-Linux%20%28Ubuntu%20%2F%20Debian%29-orange.svg?style=flat-square)](https://ubuntu.com)
[![CoreDNS](https://img.shields.io/badge/DNS-CoreDNS%201.11+-blue.svg?style=flat-square)](https://coredns.io)
[![Proxy](https://img.shields.io/badge/Forwarder-HAProxy%20%26%20Nginx%20SNI-red.svg?style=flat-square)](http://www.haproxy.org)
[![Python](https://img.shields.io/badge/Backend-Python%203.8+-yellow.svg?style=flat-square)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)

*An enterprise-grade, zero-latency gaming infrastructure designed to bypass geo-restrictions, sanctions, and ISP blocks for console and PC gamers (PlayStation 5, Xbox Series X|S, Nintendo Switch, and Windows PC).*

[Quick Install](#-one-click-quick-installation) • [Architecture](#-architecture-overview) • [Console Setup](#-console-connection-guide) • [Management CLI](#-cli-management-commands)

</div>

---

## ⚡ Highlights & Key Capabilities

- **🚀 Split-Horizon DNS Routing**: Game authentication, matchmaking lobbies, and telemetry route transparently through the low-latency egress gateway, while massive game downloads and CDN traffic resolve natively at line speed with 0% proxy overhead.
- **🎮 100% Native Console Compatibility**: Fully compatible with PS5, PS4, Xbox Series X|S, Nintendo Switch, and PC directly via network DNS settings. No VPN client, Root certificates, or router flashing needed.
- **🛡️ Transparent SNI Multiplexing**: Utilizes zero-decrypt TLS SNI routing (`ssl_preread` / HAProxy SNI inspect). Traffic remains cryptographically intact with zero latency penalty and negligible CPU usage.
- **🌐 1-Click Home IP Synchronizer**: Built-in customer portal allows gamers to re-authorize their dynamic residential ISP IP address with a single tap whenever their home modem or router reboots.
- **📊 Master Admin Control Portal**: Real-time sales & traffic KPIs, subscriber quota tracking (+10GB / +30-Day extension buttons), payment receipt approvals with screenshot preview modal, and live domain interception.
- **🔄 Two-Way Multi-Node Sync**: Kharej Master server dynamically pulls pending orders and customer subscriptions from Iran Edge nodes via automated synchronization daemon.
- **🪶 Ultra-Lightweight (No Docker Required)**: Runs on native systemd services consuming less than **15 MB of RAM** combined. Boots in under 20 milliseconds on modest 512MB/1-core cloud VPS.

---

## 🏗️ Architecture Overview

```
                      [ USER GAMING SETUP ]
       PlayStation 5 / Xbox Series X|S / PC / Switch
                             │
            ┌────────────────┴────────────────┐
            │ DNS Queries (UDP/TCP Port 53)   │
            ▼                                 ▼
┌─────────────────────────────────────────────────────────────┐
│                      IRAN EDGE NODE                         │
│                                                             │
│  [ CoreDNS Engine ]                                         │
│   ├── Normal Web / Game Updates ──► Native ISP CDN (Max Mb) │
│   └── Geo-Restricted Game Host  ──► Iran Node IP (Spoofed)  │
│                                                             │
│  [ HAProxy SNI Multiplexer (Port 443) ]                     │
│   ├── Customer Portal SNI       ──► Local Nginx + Web App   │
│   └── Gaming SNI Handshakes     ──► Kharej Egress (TCP 8443)│
└─────────────────────────────┬───────────────────────────────┘
                              │
                              │ Encrypted SNI Passthrough (Port 8443)
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    KHAREJ EGRESS GATEWAY                    │
│                                                             │
│  [ Nginx Transparent Stream Router ]                        │
│   └── Direct Transparent Egress ──► Game Servers (PSN, EA)  │
│                                                             │
│  [ Master Admin Portal (Port 9443 SSL) ]                    │
│   └── Approvals, Screenshot Viewer, Quota & Domain Manager  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 One-Click Quick Installation

### Prerequisites
- **1x Iran VPS** (Ubuntu 20.04/22.04/24.04 LTS recommended)
- **1x Kharej / Overseas VPS** (Germany, Netherlands, Finland, etc.)
- Ports `53` (UDP/TCP), `80` (TCP), `443` (TCP) open on Iran node.
- Ports `8443` (TCP), `9443` (TCP) open on Kharej node.

---

### Step 1: Deploy Kharej Egress Gateway (Run First)

Log into your **Kharej (Foreign)** server as `root` and run:

```bash
bash <(curl -sSL https://raw.githubusercontent.com/Alborzze/Smart-Dns/main/smart-dns.sh)
```

1. Select **Option 1**: `Kharej (Outside Iran) - Egress Gateway & Master Admin`.
2. Configure your Gaming SNI Port (default: `8443`).
3. (Optional) Choose `y` to deploy the **Master Admin Web Panel** with automatic Let's Encrypt SSL.

---

### Step 2: Deploy Iran Edge SmartDNS (Run Second)

Log into your **Iran** server as `root` and run:

```bash
bash <(curl -sSL https://raw.githubusercontent.com/Alborzze/Smart-Dns/main/smart-dns.sh)
```

1. Select **Option 2**: `Iran - Edge SmartDNS & Customer Portal`.
2. Enter your Kharej Server Public IP and Gaming Port (`8443`).
3. (Optional) Choose `y` to enable the **Customer Self-Service Web Portal** with automated SSL.

---

## 🎮 Console Connection Guide

Setting up your console takes under 60 seconds:

| Platform | Navigation Path | Primary DNS | Secondary DNS |
| :--- | :--- | :--- | :--- |
| **PlayStation 5** | Settings > Network > Set Up Internet Connection > Advanced Settings > DNS Manual | `<Your_Iran_IP>` | `1.1.1.1` |
| **PlayStation 4** | Settings > Network > Set Up Internet Connection > Custom > DNS Manual | `<Your_Iran_IP>` | `1.1.1.1` |
| **Xbox Series X\|S** | Settings > General > Network Settings > Advanced Settings > DNS Settings > Manual | `<Your_Iran_IP>` | `1.1.1.1` |
| **Nintendo Switch** | System Settings > Internet > Internet Settings > [Your Wi-Fi] > DNS Settings > Manual | `<Your_Iran_IP>` | `1.1.1.1` |
| **Windows PC** | Network & Internet Settings > Adapter Options > IPv4 Properties > Preferred DNS | `<Your_Iran_IP>` | `1.1.1.1` |

---

## 🎯 Supported Gaming Networks & Titles

Curated and optimized with split-horizon rules for:

- **Sony PlayStation Network (PSN)**: Account auth, PlayStation Store, Party Chat, Remote Play.
- **Microsoft Xbox Live**: Xbox Network, Game Pass, Cloud Gaming, Party Audio.
- **Electronic Arts (EA)**: EA App, EA Sports FC 24/25, Battlefield, Apex Legends.
- **Activision / Blizzard**: Battle.net, Call of Duty: Warzone, Modern Warfare III, Overwatch 2.
- **Epic Games**: Epic Online Services, Fortnite, Rocket League, Fall Guys.
- **Riot Games**: Valorant, League of Legends, Riot Client.
- **Ubisoft Connect**: Rainbow Six Siege, The Division, Ubisoft Store.
- **Nintendo Network**: eShop, Mario Kart 8 Deluxe, Splatoon 3.
- **Social & Voice**: Discord Gateway & Voice Relay endpoints.

---

## 🖥️ Management Dashboards

### 1. Customer Self-Service Portal (`https://dns.yourdomain.com`)
- **1-Tap Dynamic IP Whitelist**: Automatically syncs gamer's home modem IP without calling support.
- **Subscription Tracking**: Shows active pass details, expiration countdown, and live traffic quota (`used / total GB`).
- **Interactive Console Manual**: Visual step-by-step guides for PS5, Xbox, Switch, and PC.
- **Payment & Receipt Submission**: Bank card checkout with tracking code and receipt screenshot attachment.

### 2. Master Admin Control Hub (`https://admin.yourdomain.com:9443`)
- **Pending Approvals Queue**: View incoming customer receipts, verify transaction references, inspect payment screenshots with the built-in modal viewer, and approve with 1 click.
- **Subscriber Management**: Add or remove gamers, adjust data quotas (`+10GB`), and extend validity (`+30 Days`).
- **Live Domain Interception**: Add custom gaming or anti-sanction domains on the fly without restarting services.
- **Two-Way Node Synchronization**: Automatic background pull sync from Iran edge nodes with live sync status.

---

## 🛠️ CLI Management Commands

The installer registers the `smart-dns` utility globally on both servers:

```bash
# Check status of CoreDNS, HAProxy, Nginx, and Web Services
smart-dns status

# View active whitelisted IP addresses in Linux ipset
smart-dns clients

# Run comprehensive diagnostic benchmark (DNS latency, SNI route, BBR)
smart-dns diagnostics

# Gracefully restart all gaming and web services
smart-dns restart

# Completely purge and uninstall SmartDNS configuration
smart-dns uninstall
```

---

## 🛡️ Security & Performance Architecture

- **Linux TCP BBR**: Automatically enables BBR congestion control and tunes socket buffers for ultra-low latency packet delivery under constrained networks.
- **IPSet Kernel Acceleration**: Dynamic IP authorization uses Linux kernel `ipset hash:ip` for O(1) packet matching without CPU spikes.
- **DNS Rate-Limiting**: CoreDNS protects against amplification attacks and recursive query floods with built-in query throttling.
- **Zero Decryption**: Pass-through TLS proxy never terminates game SSL handshakes — ensuring 100% end-to-end cryptographic privacy.

---

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for more information.

---

<div align="center">
<b>Crafted for gamers worldwide. No lag. No barriers. Just play.</b>
</div>
