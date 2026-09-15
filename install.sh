#!/usr/bin/env bash
# ==============================================================================
# ALL-IN-ONE STANDALONE SMARTDNS & GAMING PROXY INSTALLER
# ==============================================================================

set -euo pipefail

# Visual formatting
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
echo "          One-Click SmartDNS & Gaming Proxy Automated Installer                 "
echo "================================================================================"
echo -e "${NC}"

# Ensure package manager dependencies exist first
echo -e "${YELLOW}[*] Updating package index and ensuring base tools...${NC}"
if command -v apt-get &>/dev/null; then
    apt-get update -y >/dev/null 2>&1 || true
    apt-get install -y curl unzip tar ca-certificates >/dev/null 2>&1 || true
elif command -v yum &>/dev/null; then
    yum install -y curl unzip tar ca-certificates >/dev/null 2>&1 || true
fi

# Parse parameters
ROLE=""
IRAN_IP=""
GERMANY_IP=""
TOKEN=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --role) ROLE="$2"; shift 2 ;;
        --iran-ip) IRAN_IP="$2"; shift 2 ;;
        --germany-ip) GERMANY_IP="$2"; shift 2 ;;
        --token) TOKEN="$2"; shift 2 ;;
        *) shift ;;
    esac
done

if [ -z "$ROLE" ]; then
    echo -e "${YELLOW}Select this server's role:${NC}"
    echo "  1) Iran Server (Edge DNS + SNI Proxy)"
    echo "  2) Germany Server (Egress Tunnel Gateway)"
    read -rp "Enter choice [1-2]: " ROLE_CHOICE
    if [ "$ROLE_CHOICE" == "1" ]; then
        ROLE="iran"
    elif [ "$ROLE_CHOICE" == "2" ]; then
        ROLE="germany"
    else
        echo -e "${RED}Invalid choice.${NC}"; exit 1
    fi
fi

if [ "$ROLE" == "iran" ]; then
    if [ -z "$IRAN_IP" ]; then
        DETECTED_IP=$(curl -s4 https://api.ipify.org || curl -s4 https://ifconfig.me || echo "")
        read -rp "Enter Public IP of this Iran server [$DETECTED_IP]: " INPUT_IRAN_IP
        IRAN_IP="${INPUT_IRAN_IP:-$DETECTED_IP}"
    fi
    if [ -z "$GERMANY_IP" ]; then
        read -rp "Enter Public IP of your German server: " GERMANY_IP
    fi
    if [ -z "$TOKEN" ]; then
        read -rp "Enter Inter-Server Tunnel Secret Token: " TOKEN
        if [ -z "$TOKEN" ]; then
            TOKEN=$(tr -dc A-Za-z0-9 </dev/urandom | head -c 32 || true)
            echo -e "Generated Token: ${GREEN}$TOKEN${NC}"
        fi
    fi
elif [ "$ROLE" == "germany" ]; then
    if [ -z "$TOKEN" ]; then
        read -rp "Enter Inter-Server Tunnel Secret Token (save this for your Iran server): " TOKEN
        if [ -z "$TOKEN" ]; then
            TOKEN=$(tr -dc A-Za-z0-9 </dev/urandom | head -c 32 || true)
            echo -e "Generated Token: ${GREEN}$TOKEN${NC}"
        fi
    fi
fi

# ------------------------------------------------------------------------------
# System Tuning (BBR & Limits)
# ------------------------------------------------------------------------------
echo -e "${YELLOW}[*] Applying Linux kernel BBR & high-throughput socket tuning...${NC}"
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

# ------------------------------------------------------------------------------
# Install Rathole binary
# ------------------------------------------------------------------------------
if ! command -v rathole &>/dev/null; then
    echo -e "${YELLOW}[*] Installing Rathole tunneling engine...${NC}"
    ARCH=$(uname -m)
    case "$ARCH" in
        x86_64) RAT_ARCH="x86_64-unknown-linux-gnu" ;;
        aarch64) RAT_ARCH="aarch64-unknown-linux-gnu" ;;
        *) echo -e "${RED}[ERROR] Architecture $ARCH not supported.${NC}"; exit 1 ;;
    esac
    
    mkdir -p /tmp/rathole_install
    curl -fSL --retry 3 "https://github.com/rathole-org/rathole/releases/download/v0.5.0/rathole-${RAT_ARCH}.zip" -o /tmp/rathole_install/rathole.zip
    unzip -qo /tmp/rathole_install/rathole.zip -d /tmp/rathole_install/
    mv /tmp/rathole_install/rathole /usr/local/bin/rathole
    chmod +x /usr/local/bin/rathole
    rm -rf /tmp/rathole_install
    echo -e "${GREEN}[+] Rathole installed successfully.${NC}"
fi

# ==============================================================================
# GERMANY SETUP
# ==============================================================================
if [ "$ROLE" == "germany" ]; then
    echo -e "${YELLOW}[*] Configuring Germany Egress Gateway...${NC}"
    mkdir -p /etc/rathole
    cat > /etc/rathole/server.toml << EOF
[server]
bind_addr = "0.0.0.0:2333"
default_token = "${TOKEN}"
heartbeat_timeout = 40

[server.transport]
type = "tcp"
[server.transport.tcp]
nodelay = true

[server.services.https]
type = "tcp"
bind_addr = "0.0.0.0:443"

[server.services.http]
type = "tcp"
bind_addr = "0.0.0.0:80"
EOF

    cat > /etc/systemd/system/rathole-server.service << 'EOF'
[Unit]
Description=Rathole Egress Server
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/rathole --server /etc/rathole/server.toml
Restart=always
RestartSec=3
LimitNOFILE=1048576

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable rathole-server
    systemctl restart rathole-server

    echo -e "\n${GREEN}================================================================${NC}"
    echo -e "${GREEN}  GERMANY EGRESS SERVER DEPLOYED SUCCESSFULLY!                  ${NC}"
    echo -e "${GREEN}================================================================${NC}"
    echo -e "Tunnel Port:  ${BOLD}2333${NC}"
    echo -e "Secret Token: ${BOLD}${TOKEN}${NC}"
    echo -e "\nCopy this token to use when configuring your Iran server.\n"
    exit 0
fi

# ==============================================================================
# IRAN SETUP
# ==============================================================================
echo -e "${YELLOW}[*] Configuring Iran Edge SmartDNS & SNI Proxy...${NC}"

# Disable port 53 systemd-resolved conflict
if systemctl is-active --quiet systemd-resolved; then
    sed -i 's/#DNSStubListener=yes/DNSStubListener=no/' /etc/systemd/resolved.conf || true
    sed -i 's/DNSStubListener=yes/DNSStubListener=no/' /etc/systemd/resolved.conf || true
    systemctl restart systemd-resolved || true
fi

# Install dependencies & CoreDNS
if command -v apt-get &>/dev/null; then
    apt-get install -y haproxy dnsutils bc >/dev/null 2>&1 || true
elif command -v yum &>/dev/null; then
    yum install -y haproxy bind-utils bc >/dev/null 2>&1 || true
fi

if ! command -v coredns &>/dev/null; then
    echo -e "${YELLOW}[*] Installing CoreDNS binary...${NC}"
    curl -fSL --retry 3 "https://github.com/coredns/coredns/releases/download/v1.11.1/coredns_1.11.1_linux_amd64.tgz" -o /tmp/coredns.tgz
    tar -xzf /tmp/coredns.tgz -C /usr/local/bin/
    chmod +x /usr/local/bin/coredns
    rm -f /tmp/coredns.tgz
    echo -e "${GREEN}[+] CoreDNS installed successfully.${NC}"
fi

# Write Gaming Domains & CoreDNS Split-Horizon Config
mkdir -p /etc/coredns
cat > /etc/coredns/gaming_rewrites.conf << EOF
    # PlayStation Network
    template IN A playstation.com { answer "{{ .Name }} 60 IN A ${IRAN_IP}"; }
    template IN A playstation.net { answer "{{ .Name }} 60 IN A ${IRAN_IP}"; }
    template IN A playstationnetwork.com { answer "{{ .Name }} 60 IN A ${IRAN_IP}"; }
    template IN A sonyentertainmentnetwork.com { answer "{{ .Name }} 60 IN A ${IRAN_IP}"; }
    template IN A auth.api.sonyentertainmentnetwork.com { answer "{{ .Name }} 60 IN A ${IRAN_IP}"; }
    template IN A auth.api.np.ac.playstation.net { answer "{{ .Name }} 60 IN A ${IRAN_IP}"; }
    template IN A session-directory.api.playstation.com { answer "{{ .Name }} 60 IN A ${IRAN_IP}"; }
    template IN A commerce.api.playstation.com { answer "{{ .Name }} 60 IN A ${IRAN_IP}"; }
    template IN A gs-sec.ww.np.dl.playstation.net { answer "{{ .Name }} 60 IN A ${IRAN_IP}"; }
    template IN A account.sonyentertainmentnetwork.com { answer "{{ .Name }} 60 IN A ${IRAN_IP}"; }
    template IN A store.playstation.com { answer "{{ .Name }} 60 IN A ${IRAN_IP}"; }

    # Xbox Live & Microsoft Gaming
    template IN A xbox.com { answer "{{ .Name }} 60 IN A ${IRAN_IP}"; }
    template IN A xboxlive.com { answer "{{ .Name }} 60 IN A ${IRAN_IP}"; }
    template IN A xboxservices.com { answer "{{ .Name }} 60 IN A ${IRAN_IP}"; }
    template IN A xsts.auth.xboxlive.com { answer "{{ .Name }} 60 IN A ${IRAN_IP}"; }
    template IN A user.auth.xboxlive.com { answer "{{ .Name }} 60 IN A ${IRAN_IP}"; }
    template IN A title.auth.xboxlive.com { answer "{{ .Name }} 60 IN A ${IRAN_IP}"; }
    template IN A multiplayer.xboxlive.com { answer "{{ .Name }} 60 IN A ${IRAN_IP}"; }

    # EA / Origin / FC / Apex
    template IN A ea.com { answer "{{ .Name }} 60 IN A ${IRAN_IP}"; }
    template IN A origin.com { answer "{{ .Name }} 60 IN A ${IRAN_IP}"; }
    template IN A signin.ea.com { answer "{{ .Name }} 60 IN A ${IRAN_IP}"; }
    template IN A accounts.ea.com { answer "{{ .Name }} 60 IN A ${IRAN_IP}"; }
    template IN A gateway.ea.com { answer "{{ .Name }} 60 IN A ${IRAN_IP}"; }
    template IN A river.data.ea.com { answer "{{ .Name }} 60 IN A ${IRAN_IP}"; }
    template IN A utas.fut.ea.com { answer "{{ .Name }} 60 IN A ${IRAN_IP}"; }

    # Activision / Call of Duty
    template IN A activision.com { answer "{{ .Name }} 60 IN A ${IRAN_IP}"; }
    template IN A callofduty.com { answer "{{ .Name }} 60 IN A ${IRAN_IP}"; }
    template IN A demonware.net { answer "{{ .Name }} 60 IN A ${IRAN_IP}"; }
    template IN A uno.demonware.net { answer "{{ .Name }} 60 IN A ${IRAN_IP}"; }
    template IN A prod.demonware.net { answer "{{ .Name }} 60 IN A ${IRAN_IP}"; }

    # Battle.net & Blizzard
    template IN A blizzard.com { answer "{{ .Name }} 60 IN A ${IRAN_IP}"; }
    template IN A battle.net { answer "{{ .Name }} 60 IN A ${IRAN_IP}"; }
    template IN A oauth.battle.net { answer "{{ .Name }} 60 IN A ${IRAN_IP}"; }
    template IN A auth.battle.net { answer "{{ .Name }} 60 IN A ${IRAN_IP}"; }

    # Ubisoft
    template IN A ubisoft.com { answer "{{ .Name }} 60 IN A ${IRAN_IP}"; }
    template IN A ubi.com { answer "{{ .Name }} 60 IN A ${IRAN_IP}"; }
    template IN A connect.ubisoft.com { answer "{{ .Name }} 60 IN A ${IRAN_IP}"; }

    # Epic Games
    template IN A epicgames.com { answer "{{ .Name }} 60 IN A ${IRAN_IP}"; }
    template IN A ol.epicgames.com { answer "{{ .Name }} 60 IN A ${IRAN_IP}"; }

    # Riot Games
    template IN A riotgames.com { answer "{{ .Name }} 60 IN A ${IRAN_IP}"; }
    template IN A auth.riotgames.com { answer "{{ .Name }} 60 IN A ${IRAN_IP}"; }

    # Nintendo
    template IN A nintendo.com { answer "{{ .Name }} 60 IN A ${IRAN_IP}"; }
    template IN A nintendo.net { answer "{{ .Name }} 60 IN A ${IRAN_IP}"; }

    # Discord
    template IN A discord.com { answer "{{ .Name }} 60 IN A ${IRAN_IP}"; }
    template IN A discord.gg { answer "{{ .Name }} 60 IN A ${IRAN_IP}"; }
    template IN A gateway.discord.gg { answer "{{ .Name }} 60 IN A ${IRAN_IP}"; }
EOF

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
    ratelimit {
        rate 150
        burst 300
    }
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

# ------------------------------------------------------------------------------
# Configure HAProxy (SNI Proxy)
# ------------------------------------------------------------------------------
cat > /etc/haproxy/haproxy.cfg << 'EOF'
global
    log /dev/log local0
    chroot /var/lib/haproxy
    user haproxy
    group haproxy
    daemon
    maxconn 65535

defaults
    log     global
    mode    tcp
    option  tcplog
    retries 3
    timeout connect 5000ms
    timeout client  50000ms
    timeout server  50000ms

frontend sni_in
    bind 0.0.0.0:443
    mode tcp
    tcp-request inspect-delay 5s
    tcp-request content accept if { req_ssl_hello_type 1 }
    default_backend backend_germany_tunnel_https

backend backend_germany_tunnel_https
    mode tcp
    server tunnel_germany 127.0.0.1:8443 check inter 3000

frontend http_in
    bind 0.0.0.0:80
    mode tcp
    default_backend backend_germany_tunnel_http

backend backend_germany_tunnel_http
    mode tcp
    server tunnel_germany_http 127.0.0.1:8080 check inter 3000
EOF

systemctl enable haproxy
systemctl restart haproxy

# ------------------------------------------------------------------------------
# Configure Rathole Client
# ------------------------------------------------------------------------------
mkdir -p /etc/rathole
cat > /etc/rathole/client.toml << EOF
[client]
remote_addr = "${GERMANY_IP}:2333"
default_token = "${TOKEN}"
heartbeat_interval = 20

[client.transport]
type = "tcp"
[client.transport.tcp]
nodelay = true

[client.services.https]
type = "tcp"
local_addr = "127.0.0.1:8443"

[client.services.http]
type = "tcp"
local_addr = "127.0.0.1:8080"
EOF

cat > /etc/systemd/system/rathole-client.service << 'EOF'
[Unit]
Description=Rathole Tunnel Client (Iran to Germany)
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/rathole --client /etc/rathole/client.toml
Restart=always
RestartSec=3
LimitNOFILE=1048576

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable rathole-client
systemctl restart rathole-client

echo -e "\n${GREEN}================================================================${NC}"
echo -e "${GREEN}  IRAN EDGE NODE DEPLOYED SUCCESSFULLY!                         ${NC}"
echo -e "${GREEN}================================================================${NC}"
echo -e "Primary DNS IP:    ${BOLD}${IRAN_IP}${NC}"
echo -e "CoreDNS Status:    ${GREEN}Active (Port 53 UDP/TCP)${NC}"
echo -e "HAProxy Status:    ${GREEN}Active (Port 443/80)${NC}"
echo -e "Connected Tunnel:  ${GREEN}${GERMANY_IP}:2333${NC}"
echo -e "\nYou can now configure your Console (PS5/Xbox) DNS to ${BOLD}${IRAN_IP}${NC}!\n"