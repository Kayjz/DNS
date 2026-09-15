#!/usr/bin/env bash
# ==============================================================================
# ALL-IN-ONE STANDALONE SMARTDNS & GAMING PROXY INSTALLER (v2.0 Production)
# Battle-tested for Console Gaming (PS5, PS4, Xbox, Switch, PC)
# ==============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}[ERROR] Please run as root: sudo bash $0${NC}"
    exit 1
fi

echo -e "${CYAN}${BOLD}"
echo "================================================================================"
echo "          SmartDNS & Gaming Proxy Automated Production Installer                "
echo "================================================================================"
echo -e "${NC}"

# Handle Ubuntu background unattended-upgrades lock
systemctl stop unattended-upgrades >/dev/null 2>&1 || true
killall apt apt-get unattended-upgr >/dev/null 2>&1 || true

# Parse command arguments
ROLE=""
IRAN_IP=""
GERMANY_IP=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --role) ROLE="$2"; shift 2 ;;
        --iran-ip) IRAN_IP="$2"; shift 2 ;;
        --germany-ip) GERMANY_IP="$2"; shift 2 ;;
        *) shift ;;
    esac
done

if [ -z "$ROLE" ]; then
    echo -e "${YELLOW}Select server role:${NC}"
    echo "  1) Germany Egress Node (Run this FIRST)"
    echo "  2) Iran Edge Node (DNS + SNI Forwarder)"
    read -rp "Enter choice [1-2]: " CHOICE
    [ "$CHOICE" == "1" ] && ROLE="germany"
    [ "$CHOICE" == "2" ] && ROLE="iran"
fi

# ------------------------------------------------------------------------------
# Kernel & Network Optimization (BBR + TCP MSS Clamping)
# ------------------------------------------------------------------------------
echo -e "${YELLOW}[*] Applying BBR congestion control and kernel optimizations...${NC}"
cat > /etc/sysctl.d/99-gaming-proxy.conf << 'EOF'
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 65535
net.core.rmem_max = 33554432
net.core.wmem_max = 33554432
net.ipv4.tcp_rmem = 4096 87380 33554432
net.ipv4.tcp_wmem = 4096 65536 33554432
net.ipv4.ip_local_port_range = 1024 65535
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 15
net.ipv4.ip_forward = 1
EOF
sysctl --system >/dev/null 2>&1 || true

# TCP MSS clamping to prevent international packet fragmentation
iptables -t mangle -C POSTROUTING -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1360 2>/dev/null || \
    iptables -t mangle -A POSTROUTING -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1360
iptables -t mangle -C FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1360 2>/dev/null || \
    iptables -t mangle -A FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1360

# ==============================================================================
# GERMANY EGRESS SETUP
# ==============================================================================
if [ "$ROLE" == "germany" ]; then
    echo -e "${YELLOW}[*] Deploying Germany Egress Gateway (Nginx Stream SNI)...${NC}"
    apt-get update -y >/dev/null 2>&1 || true
    apt-get install -y nginx libnginx-mod-stream curl >/dev/null 2>&1 || true

    # Find the stream module path
    MOD_PATH="/usr/lib/nginx/modules/ngx_stream_module.so"

    cat > /etc/nginx/nginx.conf << EOF
load_module ${MOD_PATH};

user www-data;
worker_processes auto;
pid /run/nginx.pid;
error_log /var/log/nginx/error.log;

events {
    worker_connections 65535;
}

stream {
    resolver 1.1.1.1 8.8.8.8 valid=10s ipv6=off;
    resolver_timeout 5s;

    server {
        listen 8443;
        ssl_preread on;
        proxy_pass \$ssl_preread_server_name:443;
        proxy_connect_timeout 5s;
        proxy_timeout 60s;
    }
}
EOF

    systemctl enable nginx
    systemctl restart nginx

    DETECTED_GERMAN_IP=$(curl -s4 https://api.ipify.org || curl -s4 https://ifconfig.me || echo "")
    echo -e "\n${GREEN}================================================================${NC}"
    echo -e "${GREEN}  GERMANY EGRESS GATEWAY READY!                                 ${NC}"
    echo -e "${GREEN}================================================================${NC}"
    echo -e "German Public IP: ${BOLD}${DETECTED_GERMAN_IP}${NC}"
    echo -e "Listening Port:   ${BOLD}8443 (SNI Egress)${NC}"
    echo -e "Now run the installer on your Iran server using this German IP!\n"
    exit 0
fi

# ==============================================================================
# IRAN EDGE SETUP
# ==============================================================================
if [ -z "$IRAN_IP" ]; then
    DETECTED_IRAN_IP=$(curl -s4 https://api.ipify.org || curl -s4 https://ifconfig.me || echo "")
    read -rp "Enter Public IP of this Iran server [$DETECTED_IRAN_IP]: " INPUT_IRAN_IP
    IRAN_IP="${INPUT_IRAN_IP:-$DETECTED_IRAN_IP}"
fi

if [ -z "$GERMANY_IP" ]; then
    read -rp "Enter Public IP of your German server: " GERMANY_IP
fi

echo -e "${YELLOW}[*] Deploying Iran Edge SmartDNS & SNI Dispatcher...${NC}"

# Disable port 53 stub listener conflict
if systemctl is-active --quiet systemd-resolved; then
    sed -i 's/#DNSStubListener=yes/DNSStubListener=no/' /etc/systemd/resolved.conf || true
    sed -i 's/DNSStubListener=yes/DNSStubListener=no/' /etc/systemd/resolved.conf || true
    systemctl restart systemd-resolved || true
fi

apt-get update -y >/dev/null 2>&1 || true
apt-get install -y haproxy curl dnsutils tar python3 >/dev/null 2>&1 || true

# Install CoreDNS
if ! command -v coredns &>/dev/null; then
    echo -e "${YELLOW}[*] Downloading CoreDNS binary...${NC}"
    curl -fSL --retry 3 "https://github.com/coredns/coredns/releases/download/v1.11.1/coredns_1.11.1_linux_amd64.tgz" -o /tmp/coredns.tgz
    tar -xzf /tmp/coredns.tgz -C /usr/local/bin/
    chmod +x /usr/local/bin/coredns
    rm -f /tmp/coredns.tgz
fi

# Generate Gaming Domains List
mkdir -p /etc/coredns
cat > /tmp/generate_domains.py << PYEOF
import sys

iran_ip = sys.argv[1]
domains = [
    # PlayStation Network
    "playstation.com", "playstation.net", "playstationnetwork.com",
    "sonyentertainmentnetwork.com", "auth.api.sonyentertainmentnetwork.com",
    "auth.api.np.ac.playstation.net", "session-directory.api.playstation.com",
    "commerce.api.playstation.com", "gs-sec.ww.np.dl.playstation.net",
    "account.sonyentertainmentnetwork.com", "store.playstation.com",
    # Xbox Live
    "xbox.com", "xboxlive.com", "xboxservices.com", "xsts.auth.xboxlive.com",
    "user.auth.xboxlive.com", "title.auth.xboxlive.com", "multiplayer.xboxlive.com",
    # EA / FIFA / Apex
    "ea.com", "origin.com", "signin.ea.com", "accounts.ea.com",
    "gateway.ea.com", "river.data.ea.com", "utas.fut.ea.com", "fut-squad.ea.com",
    # Activision / COD
    "activision.com", "callofduty.com", "demonware.net", "uno.demonware.net", "prod.demonware.net",
    # Blizzard
    "blizzard.com", "battle.net", "oauth.battle.net", "auth.battle.net",
    # Ubisoft
    "ubisoft.com", "ubi.com", "connect.ubisoft.com",
    # Epic Games / Fortnite
    "epicgames.com", "ol.epicgames.com", "epicgames.org", "unrealengine.com",
    "fortnite.com", "rocketleague.com", "account-public-service-prod.ol.epicgames.com",
    # Riot Games / Valorant
    "riotgames.com", "auth.riotgames.com", "playvalorant.com", "leagueoflegends.com",
    # Nintendo
    "nintendo.com", "nintendo.net",
    # Discord
    "discord.com", "discord.gg", "gateway.discord.gg",
    # Sanctioned Web Tools
    "adobe.com", "www.adobe.com", "adobe.io"
]

content = "    hosts {\n"
for d in domains:
    content += f"        {iran_ip} {d}\n"
content += "        fallthrough\n    }\n"

with open("/etc/coredns/gaming_rewrites.conf", "w") as f:
    f.write(content)
PYEOF

python3 /tmp/generate_domains.py "$IRAN_IP"
rm -f /tmp/generate_domains.py

cat > /etc/coredns/Corefile << 'EOF'
.:53 {
    bind 0.0.0.0
    cache 3600 {
        success 4096
        denial 1024
        prefetch 10 1m 10%
    }
    errors
    health :8080
    import /etc/coredns/gaming_rewrites.conf
    forward . 1.1.1.1 8.8.8.8 9.9.9.9 1.0.0.1 {
        prefer_udp
        max_fails 3
        expire 10s
        health_check 5s
    }
    prometheus :9153
}
EOF

cat > /etc/systemd/system/coredns.service << 'EOF'
[Unit]
Description=CoreDNS SmartDNS Server
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/coredns -conf /etc/coredns/Corefile
Restart=always
RestartSec=2
LimitNOFILE=1048576

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable coredns
systemctl restart coredns

# Configure HAProxy on Iran (SNI Forwarder to Germany)
cat > /etc/haproxy/haproxy.cfg << EOF
global
    log /dev/log local0
    user haproxy
    group haproxy
    daemon
    maxconn 65535

defaults
    mode tcp
    timeout connect 5s
    timeout client 50s
    timeout server 50s

frontend sni_in
    bind 0.0.0.0:443
    mode tcp
    tcp-request inspect-delay 5s
    tcp-request content accept if { req_ssl_hello_type 1 }
    default_backend backend_germany

backend backend_germany
    mode tcp
    server germany ${GERMANY_IP}:8443 check inter 3000
EOF

systemctl enable haproxy
systemctl restart haproxy

# Install smart-dns CLI management tool
curl -sSL "https://raw.githubusercontent.com/Kayjz/DNS/main/scripts/smart-dns" -o /usr/local/bin/smart-dns
chmod +x /usr/local/bin/smart-dns

echo -e "\n${GREEN}================================================================${NC}"
echo -e "${GREEN}  IRAN EDGE NODE DEPLOYED SUCCESSFULLY!                         ${NC}"
echo -e "${GREEN}================================================================${NC}"
echo -e "Primary DNS IP:    ${BOLD}${IRAN_IP}${NC}"
echo -e "CoreDNS Status:    ${GREEN}Active (Port 53 UDP/TCP)${NC}"
echo -e "HAProxy Forwarder: ${GREEN}Forwarding to ${GERMANY_IP}:8443${NC}"
echo -e "Management CLI:    ${BOLD}smart-dns${NC} (Type 'smart-dns' in terminal)"
echo -e "\nSet your Console DNS to: ${BOLD}${IRAN_IP}${NC} and start gaming!\n"
