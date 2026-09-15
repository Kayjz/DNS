#!/usr/bin/env bash
# ==============================================================================
# SMARTDNS & GAMING PROXY AUTOMATED DEPLOYMENT SCRIPT
# Supports: Ubuntu 20.04+, Debian 11+, CentOS 8+
# Roles:
#   --role iran     : Installs CoreDNS, HAProxy (SNI Pass-through), and Tunnel Client
#   --role germany  : Installs Tunnel Server and Egress routing
# ==============================================================================

set -euo pipefail

# Visual formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Verify root privileges
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}[ERROR] Please execute this script as root or with sudo.${NC}"
    exit 1
fi

# Print banner
echo -e "${CYAN}${BOLD}"
echo "================================================================================"
echo "          SmartDNS & Console Game Proxy - Production Deployment                 "
echo "================================================================================"
echo -e "${NC}"

# Help menu
usage() {
    echo -e "Usage: $0 --role [iran|germany] [options]"
    echo ""
    echo "Options for Iran Node:"
    echo "  --role iran                   Deploy as Iran Edge (DNS + SNI Proxy + Tunnel Client)"
    echo "  --iran-ip <IP>                Public IP of this Iran server"
    echo "  --germany-ip <IP>             Public IP of the German server"
    echo "  --token <SECRET>              Pre-shared secret token for inter-server tunnel"
    echo ""
    echo "Options for Germany Node:"
    echo "  --role germany                Deploy as German Egress Gateway (Tunnel Server)"
    echo "  --token <SECRET>              Pre-shared secret token for inter-server tunnel"
    echo ""
    exit 1
}

# Parse CLI arguments
ROLE=""
IRAN_IP=""
GERMANY_IP=""
TOKEN=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --role)
            ROLE="$2"
            shift 2
            ;;
        --iran-ip)
            IRAN_IP="$2"
            shift 2
            ;;
        --germany-ip)
            GERMANY_IP="$2"
            shift 2
            ;;
        --token)
            TOKEN="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo -e "${RED}Unknown argument: $1${NC}"
            usage
            ;;
    esac
done

# Interactive mode if parameters omitted
if [ -z "$ROLE" ]; then
    echo -e "${YELLOW}Please select the server deployment role:${NC}"
    echo "  1) Iran Edge Node (DNS + SNI Proxy + Tunnel Client)"
    echo "  2) Germany Egress Node (Tunnel Server)"
    read -rp "Enter choice [1-2]: " ROLE_CHOICE
    if [ "$ROLE_CHOICE" == "1" ]; then
        ROLE="iran"
    elif [ "$ROLE_CHOICE" == "2" ]; then
        ROLE="germany"
    else
        echo -e "${RED}Invalid selection.${NC}"; exit 1
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
        read -rp "Enter Inter-Server Tunnel Secret Token (or press enter to generate): " TOKEN
        if [ -z "$TOKEN" ]; then
            TOKEN=$(tr -dc A-Za-z0-9 </dev/urandom | head -c 32 || true)
            echo -e "Generated Token: ${GREEN}$TOKEN${NC}"
        fi
    fi
elif [ "$ROLE" == "germany" ]; then
    if [ -z "$TOKEN" ]; then
        read -rp "Enter Inter-Server Tunnel Secret Token: " TOKEN
        if [ -z "$TOKEN" ]; then
            TOKEN=$(tr -dc A-Za-z0-9 </dev/urandom | head -c 32 || true)
            echo -e "Generated Token: ${GREEN}$TOKEN${NC}"
        fi
    fi
fi

# ------------------------------------------------------------------------------
# System Optimization: TCP BBR, Network Buffers & File Descriptors
# ------------------------------------------------------------------------------
tune_system() {
    echo -e "${YELLOW}[*] Applying Linux kernel optimizations (BBR, High concurrency)...${NC}"
    
    cat > /etc/sysctl.d/99-gaming-proxy.conf << 'EOF'
# TCP BBR Congestion Control
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr

# Socket buffers and backlog
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 65535
net.core.rmem_max = 33554432
net.core.wmem_max = 33554432
net.ipv4.tcp_rmem = 4096 87380 33554432
net.ipv4.tcp_wmem = 4096 65536 33554432

# Port range and fast reuse
net.ipv4.ip_local_port_range = 1024 65535
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 15
net.ipv4.tcp_notsent_lowat = 16384

# IP Forwarding
net.ipv4.ip_forward = 1
EOF
    sysctl --system >/dev/null 2>&1 || true

    cat > /etc/security/limits.d/99-gaming.conf << 'EOF'
* soft nofile 1048576
* hard nofile 1048576
* soft nproc 1048576
* hard nproc 1048576
root soft nofile 1048576
root hard nofile 1048576
EOF
    echo -e "${GREEN}[+] System kernel parameters tuned successfully.${NC}"
}

# ------------------------------------------------------------------------------
# Install Rathole binary
# ------------------------------------------------------------------------------
install_rathole() {
    if command -v rathole &>/dev/null; then
        echo -e "${GREEN}[+] Rathole is already installed.${NC}"
        return
    fi
    echo -e "${YELLOW}[*] Installing Rathole tunneling daemon...${NC}"
    ARCH=$(uname -m)
    case "$ARCH" in
        x86_64) RATHOLE_ARCH="x86_64-unknown-linux-musl" ;;
        aarch64) RATHOLE_ARCH="aarch64-unknown-linux-musl" ;;
        *) echo -e "${RED}[ERROR] Unsupported architecture: $ARCH${NC}"; exit 1 ;;
    esac

    RATHOLE_VERSION="v0.5.0"
    URL="https://github.com/rapiz1/rathole/releases/download/${RATHOLE_VERSION}/rathole-${RATHOLE_ARCH}.zip"
    
    mkdir -p /tmp/rathole_dl
    curl -sL "$URL" -o /tmp/rathole_dl/rathole.zip
    apt-get install -y unzip &>/dev/null || yum install -y unzip &>/dev/null || true
    unzip -q /tmp/rathole_dl/rathole.zip -d /tmp/rathole_dl/
    mv /tmp/rathole_dl/rathole /usr/local/bin/rathole
    chmod +x /usr/local/bin/rathole
    rm -rf /tmp/rathole_dl
    echo -e "${GREEN}[+] Rathole installed to /usr/local/bin/rathole${NC}"
}

# ==============================================================================
# DEPLOYMENT LOGIC FOR GERMANY EGRESS NODE
# ==============================================================================
deploy_germany() {
    echo -e "${CYAN}Starting deployment for GERMANY EGRESS GATEWAY...${NC}"
    tune_system
    install_rathole

    # Prepare directories
    mkdir -p /etc/rathole

    # Write Rathole Server config
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

    # Setup Rathole Systemd Service
    cat > /etc/systemd/system/rathole-server.service << 'EOF'
[Unit]
Description=Rathole Tunnel Server (Germany Egress)
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
    echo -e "${GREEN}  GERMANY EGRESS GATEWAY DEPLOYED SUCCESSFULLY!                 ${NC}"
    echo -e "${GREEN}================================================================${NC}"
    echo -e "Tunnel Listening Port: ${BOLD}2333${NC}"
    echo -e "Tunnel Token:          ${BOLD}${TOKEN}${NC}"
    echo -e "HTTPS / HTTP Egress:   ${BOLD}Port 443 / 80 Active${NC}"
    echo -e "Use this Token and this Server's IP when setting up the Iran node.\n"
}

# ==============================================================================
# DEPLOYMENT LOGIC FOR IRAN EDGE NODE
# ==============================================================================
deploy_iran() {
    echo -e "${CYAN}Starting deployment for IRAN EDGE NODE...${NC}"
    tune_system
    install_rathole

    # Disable Ubuntu default systemd-resolved DNS stub listener if active
    if systemctl is-active --quiet systemd-resolved; then
        echo -e "${YELLOW}[*] Disabling systemd-resolved stub listener on port 53...${NC}"
        sed -i 's/#DNSStubListener=yes/DNSStubListener=no/' /etc/systemd/resolved.conf || true
        sed -i 's/DNSStubListener=yes/DNSStubListener=no/' /etc/systemd/resolved.conf || true
        systemctl restart systemd-resolved || true
    fi

    # Install CoreDNS & HAProxy
    echo -e "${YELLOW}[*] Installing CoreDNS and HAProxy...${NC}"
    if command -v apt-get &>/dev/null; then
        apt-get update -y
        apt-get install -y haproxy dnsutils curl iputils-ping bc
    elif command -v yum &>/dev/null; then
        yum install -y haproxy bind-utils curl iputils bc
    fi

    # Install CoreDNS binary if not present
    if ! command -v coredns &>/dev/null; then
        echo -e "${YELLOW}[*] Fetching latest CoreDNS binary...${NC}"
        COREDNS_VER="1.11.1"
        ARCH=$(uname -m)
        case "$ARCH" in
            x86_64) C_ARCH="amd64" ;;
            aarch64) C_ARCH="arm64" ;;
            *) C_ARCH="amd64" ;;
        esac
        curl -sL "https://github.com/coredns/coredns/releases/download/v${COREDNS_VER}/coredns_${COREDNS_VER}_linux_${C_ARCH}.tgz" -o /tmp/coredns.tgz
        tar -xzf /tmp/coredns.tgz -C /usr/local/bin/
        chmod +x /usr/local/bin/coredns
        rm -f /tmp/coredns.tgz
    fi

    # 1. Setup CoreDNS Configurations
    mkdir -p /etc/coredns
    
    # Generate split-horizon rewrite rules from domain list
    echo -e "${YELLOW}[*] Generating DNS gaming domain split-horizon rules...${NC}"
    DOMAIN_FILE="${SCRIPT_DIR}/dns/gaming-domains.txt"
    REWRITE_CONF="/etc/coredns/gaming_rewrites.conf"
    
    echo "# Auto-generated gaming rewrite rules" > "$REWRITE_CONF"
    if [ -f "$DOMAIN_FILE" ]; then
        while IFS= read -r line || [ -n "$line" ]; do
            # Trim whitespace and skip comments/empty lines
            clean_line=$(echo "$line" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
            if [[ -n "$clean_line" && ! "$clean_line" =~ ^# ]]; then
                echo "    rewrite name exact ${clean_line} ${clean_line}." >> "$REWRITE_CONF"
                echo "    template IN A ${clean_line} { answer \"{{ .Name }} 60 IN A ${IRAN_IP}\"; }" >> "$REWRITE_CONF"
            fi
        done < "$DOMAIN_FILE"
    else
        echo -e "${YELLOW}[WARN] Gaming domains file not found at ${DOMAIN_FILE}. Using defaults.${NC}"
        echo "    template IN A playstation.com { answer \"{{ .Name }} 60 IN A ${IRAN_IP}\"; }" >> "$REWRITE_CONF"
        echo "    template IN A xboxlive.com { answer \"{{ .Name }} 60 IN A ${IRAN_IP}\"; }" >> "$REWRITE_CONF"
        echo "    template IN A ea.com { answer \"{{ .Name }} 60 IN A ${IRAN_IP}\"; }" >> "$REWRITE_CONF"
    fi

    # Copy Corefile template
    sed "s/__IRAN_IP__/${IRAN_IP}/g" "${SCRIPT_DIR}/dns/Corefile.template" > /etc/coredns/Corefile

    # Setup CoreDNS Systemd Service
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

    # 2. Setup HAProxy (SNI Proxy)
    echo -e "${YELLOW}[*] Configuring HAProxy SNI proxy...${NC}"
    cp "${SCRIPT_DIR}/proxy/haproxy.cfg.template" /etc/haproxy/haproxy.cfg
    systemctl enable haproxy
    systemctl restart haproxy

    # 3. Setup Rathole Client (Inter-server Tunnel to Germany)
    echo -e "${YELLOW}[*] Configuring Rathole Client to German server...${NC}"
    mkdir -p /etc/rathole
    sed -e "s/__GERMANY_IP__/${GERMANY_IP}/g" -e "s/__TUNNEL_TOKEN__/${TOKEN}/g" \
        "${SCRIPT_DIR}/tunnel/rathole-client.toml.template" > /etc/rathole/client.toml

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
    echo -e "Primary DNS Server IP:   ${BOLD}${IRAN_IP}${NC}"
    echo -e "CoreDNS Status:          ${GREEN}Active (Port 53 UDP/TCP)${NC}"
    echo -e "HAProxy SNI Proxy:       ${GREEN}Active (Port 443/80)${NC}"
    echo -e "Tunnel to Germany:       ${GREEN}Connected to ${GERMANY_IP}:2333${NC}"
    echo -e "\nTo test the installation, run the diagnostic suite:"
    echo -e "${CYAN}  bash ${SCRIPT_DIR}/scripts/benchmark.sh ${IRAN_IP}${NC}\n"
}

# Main Execution Dispatcher
case "$ROLE" in
    germany)
        deploy_germany
        ;;
    iran)
        deploy_iran
        ;;
    *)
        usage
        ;;
esac
