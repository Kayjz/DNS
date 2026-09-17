#!/usr/bin/env bash
# ==============================================================================
# SMART-DNS DISTRIBUTED SYSTEM: KHAREJ ADMIN + IRAN CUSTOMER PORTALS
# GitHub: https://github.com/Kayjz/DNS
# ==============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}[ERROR] Please run this script as root (sudo -i or sudo bash)${NC}"
    exit 1
fi

detect_state() {
    if [ -f "/etc/coredns/Corefile" ]; then
        echo "iran"
    elif [ -f "/etc/nginx/nginx.conf" ] && grep -q "ssl_preread" /etc/nginx/nginx.conf 2>/dev/null; then
        echo "kharej"
    else
        echo "none"
    fi
}

get_public_ip() {
    local IP=""
    if [ -f "/etc/coredns/gaming_rewrites.conf" ]; then
        IP=$(grep -oP '(?<=hosts \{[\r\n\s]{1,100})\d+(\.\d+){3}' /etc/coredns/gaming_rewrites.conf 2>/dev/null | head -n1 || true)
    fi
    if [ -z "$IP" ]; then
        IP=$(curl -s4 --max-time 3 https://api.ipify.org 2>/dev/null || true)
    fi
    if [ -z "$IP" ]; then
        IP=$(curl -s4 --max-time 3 https://ifconfig.me 2>/dev/null || true)
    fi
    if [ -z "$IP" ]; then
        IP=$(ip -4 addr show eth0 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | head -n1 || echo "127.0.0.1")
    fi
    echo "$IP"
}

print_banner() {
    clear
    echo -e "${CYAN}${BOLD}"
    echo "================================================================================"
    echo "             ? SMART-DNS & DISTRIBUTED GAMING PLATFORM ?                      "
    echo "================================================================================"
    echo -e "${NC}"
}

apply_kernel_optimizations() {
    echo -e "${YELLOW}[*] Applying BBR congestion control and kernel optimizations...${NC}"
    cat > /etc/sysctl.d/99-smartdns-proxy.conf << 'EOF'
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

    iptables -t mangle -C POSTROUTING -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1360 2>/dev/null || \
        iptables -t mangle -A POSTROUTING -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1360
    iptables -t mangle -C FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1360 2>/dev/null || \
        iptables -t mangle -A FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1360
}

register_cli_command() {
    curl -sSL "https://raw.githubusercontent.com/Kayjz/DNS/main/smart-dns.sh" -o /usr/local/bin/smart-dns
    chmod +x /usr/local/bin/smart-dns
}

# ==============================================================================
# INSTALLATION: KHAREJ (GERMANY / EUROPE) WITH ADMIN PANEL
# ==============================================================================
install_kharej_wizard() {
    print_banner
    echo -e "${MAGENTA}${BOLD}>>> INSTALLING KHAREJ EGRESS GATEWAY & MASTER ADMIN PORTAL <<<${NC}\n"

    DETECTED_IP=$(get_public_ip)
    echo -e "Detected Kharej Public IP: ${GREEN}${DETECTED_IP}${NC}"
    read -rp "Enter Port for Gaming SNI Egress [Default: 8443]: " PORT_INPUT
    KHAREJ_PORT="${PORT_INPUT:-8443}"

    echo ""
    echo -e "${CYAN}--- Admin Panel Setup ---${NC}"
    read -rp "Do you want to install the Master Admin Web Panel on this Kharej server? [y/N]: " WANT_ADMIN
    ADMIN_DOMAIN=""
    ADMIN_PORT="9443"
    ADMIN_PASS=""

    if [[ "$WANT_ADMIN" =~ ^[Yy]$ ]]; then
        read -rp "Enter Domain for Admin Panel (e.g. admin.yourdomain.com): " ADMIN_DOMAIN
        read -rp "Enter Custom Port for Admin Panel [Default: 9443]: " PORT_IN
        ADMIN_PORT="${PORT_IN:-9443}"

        read -rp "Enter Admin Password (press Enter to auto-generate): " PASS_IN
        if [ -z "$PASS_IN" ]; then
            ADMIN_PASS=$(tr -dc A-Za-z0-9_ </dev/urandom | head -c 16 || true)
            echo -e "Generated Admin Password: ${GREEN}${ADMIN_PASS}${NC}"
        else
            ADMIN_PASS="$PASS_IN"
        fi
    fi

    echo -e "\n${YELLOW}[1/4] Updating package repositories and installing base packages...${NC}"
    systemctl stop unattended-upgrades >/dev/null 2>&1 || true
    killall apt apt-get unattended-upgr >/dev/null 2>&1 || true

    if command -v apt-get &>/dev/null; then
        apt-get update -y >/dev/null 2>&1 || true
        apt-get install -y nginx libnginx-mod-stream curl certbot python3-certbot-nginx iptables >/dev/null 2>&1 || true
    fi

    echo -e "${YELLOW}[2/4] Applying TCP BBR & kernel optimizations...${NC}"
    apply_kernel_optimizations

    echo -e "${YELLOW}[3/4] Configuring Nginx transparent SNI routing on port ${KHAREJ_PORT}...${NC}"
    MOD_LOAD=""
    if [ -f "/usr/lib/nginx/modules/ngx_stream_module.so" ]; then
        MOD_LOAD="load_module /usr/lib/nginx/modules/ngx_stream_module.so;"
    fi

    cat > /etc/nginx/nginx.conf << EOF
${MOD_LOAD}

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
        listen ${KHAREJ_PORT};
        ssl_preread on;
        proxy_pass \$ssl_preread_server_name:443;
        proxy_connect_timeout 5s;
        proxy_timeout 60s;
    }
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    sendfile on;
    keepalive_timeout 65;
    include /etc/nginx/conf.d/*.conf;
}
EOF

    # Configure Admin Panel Web Server & SSL if requested
    if [ -n "$ADMIN_DOMAIN" ]; then
        echo -e "${YELLOW}[*] Requesting SSL certificate for ${ADMIN_DOMAIN}...${NC}"
        mkdir -p /var/www/html /etc/nginx/conf.d
        cat > "/etc/nginx/conf.d/admin_panel.conf" << EOF
server {
    listen 80;
    server_name ${ADMIN_DOMAIN};
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
    location / {
        return 301 https://\$host:${ADMIN_PORT}\$request_uri;
    }
}
EOF
        systemctl restart nginx 2>/dev/null || true

        # Use Nginx or standalone for cert acquisition
        certbot certonly --nginx -d "$ADMIN_DOMAIN" --non-interactive --agree-tos --register-unsafely-without-email 2>/dev/null || \
            certbot certonly --standalone -d "$ADMIN_DOMAIN" --non-interactive --agree-tos --register-unsafely-without-email 2>/dev/null || true

        if [ -d "/etc/letsencrypt/live/${ADMIN_DOMAIN}" ]; then
            cat > "/etc/nginx/conf.d/admin_panel.conf" << EOF
server {
    listen 80;
    server_name ${ADMIN_DOMAIN};
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
    location / {
        return 301 https://\$host:${ADMIN_PORT}\$request_uri;
    }
}

server {
    listen ${ADMIN_PORT} ssl;
    server_name ${ADMIN_DOMAIN};

    ssl_certificate /etc/letsencrypt/live/${ADMIN_DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${ADMIN_DOMAIN}/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
        else
            echo -e "${YELLOW}[WARN] Could not issue SSL automatically. Admin panel will run on HTTP port ${ADMIN_PORT}.${NC}"
            cat > "/etc/nginx/conf.d/admin_panel.conf" << EOF
server {
    listen ${ADMIN_PORT};
    server_name ${ADMIN_DOMAIN};

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOF
        fi

        mkdir -p /opt/smartdns-admin
        curl -sSL "https://raw.githubusercontent.com/Kayjz/DNS/main/panel/admin_server.py?v=$(date +%s)" -o /opt/smartdns-admin/admin_server.py
        chmod +x /opt/smartdns-admin/admin_server.py

        # Setup systemd service for Admin Portal (Python 3)
        cat > /etc/systemd/system/smartdns-admin.service << SVC
[Unit]
Description=SmartDNS Master Admin Portal
After=network.target

[Service]
Type=simple
Environment=ADMIN_PASSWORD="${ADMIN_PASS}"
WorkingDirectory=/opt/smartdns-admin
ExecStart=/usr/bin/python3 /opt/smartdns-admin/admin_server.py
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
SVC

        systemctl daemon-reload
        systemctl enable smartdns-admin
        systemctl restart smartdns-admin
    fi

    systemctl enable nginx
    systemctl restart nginx
    register_cli_command

    echo -e "\n${GREEN}================================================================${NC}"
    echo -e "${GREEN}  ? KHAREJ EGRESS & ADMIN GATEWAY DEPLOYED SUCCESSFULLY!        ${NC}"
    echo -e "${GREEN}================================================================${NC}"
    echo -e "Kharej Server IP:    ${BOLD}${DETECTED_IP}${NC}"
    echo -e "Gaming Egress Port:  ${BOLD}${KHAREJ_PORT}${NC}"
    if [ -n "$ADMIN_DOMAIN" ]; then
        PROTO="https"
        [ ! -d "/etc/letsencrypt/live/${ADMIN_DOMAIN}" ] && PROTO="http"
        echo -e "Admin Web Portal:    ${BOLD}${PROTO}://${ADMIN_DOMAIN}:${ADMIN_PORT}/admin${NC}"
        echo -e "Admin Username:      ${BOLD}admin${NC}"
        echo -e "Admin Password:      ${BOLD}${ADMIN_PASS}${NC}"
    fi
    echo -e "Management Command:  Type ${CYAN}smart-dns${NC} anytime to open the menu"
    echo -e "----------------------------------------------------------------\n"
    read -rp "Press Enter to return to main menu..."
}

# ==============================================================================
# INSTALLATION: IRAN NODE WITH CUSTOMER PORTAL
# ==============================================================================
install_iran_wizard() {
    print_banner
    echo -e "${GREEN}${BOLD}>>> INSTALLING IRAN EDGE SMARTDNS & CUSTOMER PORTAL <<<${NC}\n"

    DETECTED_IP=$(get_public_ip)
    read -rp "Enter Public IP of this Iran server [Default: ${DETECTED_IP}]: " IRAN_IP_INPUT
    IRAN_IP="${IRAN_IP_INPUT:-$DETECTED_IP}"

    read -rp "Enter Kharej (Outside Iran) Server IP: " KHAREJ_IP
    while [ -z "$KHAREJ_IP" ]; do
        echo -e "${RED}Kharej IP is required!${NC}"
        read -rp "Enter Kharej (Outside Iran) Server IP: " KHAREJ_IP
    done

    read -rp "Enter Kharej Server Port [Default: 8443]: " KHAREJ_PORT_INPUT
    KHAREJ_PORT="${KHAREJ_PORT_INPUT:-8443}"

    echo ""
    echo -e "${CYAN}--- Customer Portal Setup ---${NC}"
    read -rp "Do you want to install the Customer Dashboard on this Iran server? [y/N]: " WANT_CUSTOMER
    CUSTOMER_DOMAIN=""

    if [[ "$WANT_CUSTOMER" =~ ^[Yy]$ ]]; then
        read -rp "Enter Domain for Customer Portal (e.g. dns.yourdomain.com): " CUSTOMER_DOMAIN
    fi

    echo -e "\n${YELLOW}[1/5] Disabling systemd-resolved conflict on port 53...${NC}"
    if systemctl is-active --quiet systemd-resolved; then
        sed -i 's/#DNSStubListener=yes/DNSStubListener=no/' /etc/systemd/resolved.conf || true
        sed -i 's/DNSStubListener=yes/DNSStubListener=no/' /etc/systemd/resolved.conf || true
        systemctl restart systemd-resolved || true
    fi

    echo -e "${YELLOW}[2/5] Updating packages and installing dependencies...${NC}"
    systemctl stop unattended-upgrades >/dev/null 2>&1 || true
    killall apt apt-get unattended-upgr >/dev/null 2>&1 || true

    apt-get update -y >/dev/null 2>&1 || true
    apt-get install -y haproxy nginx certbot python3-certbot-nginx curl dnsutils tar python3 iptables ipset >/dev/null 2>&1 || true
    systemctl stop apache2 >/dev/null 2>&1 || true
    systemctl disable apache2 >/dev/null 2>&1 || true
    rm -f /etc/nginx/sites-enabled/default /etc/nginx/conf.d/default.conf

    echo -e "${YELLOW}[3/5] Applying TCP BBR & socket optimizations...${NC}"
    apply_kernel_optimizations

    echo -e "${YELLOW}[4/5] Installing CoreDNS & generating gaming rules...${NC}"
    if ! command -v coredns &>/dev/null; then
        curl -fSL --retry 3 "https://github.com/coredns/coredns/releases/download/v1.11.1/coredns_1.11.1_linux_amd64.tgz" -o /tmp/coredns.tgz
        tar -xzf /tmp/coredns.tgz -C /usr/local/bin/
        chmod +x /usr/local/bin/coredns
        rm -f /tmp/coredns.tgz
    fi

    mkdir -p /etc/coredns
    cat > /tmp/gen_domains.py << PYEOF
import sys
iran_ip = sys.argv[1]
domains = [
    "playstation.com", "playstation.net", "playstationnetwork.com",
    "sonyentertainmentnetwork.com", "auth.api.sonyentertainmentnetwork.com",
    "auth.api.np.ac.playstation.net", "session-directory.api.playstation.com",
    "commerce.api.playstation.com", "gs-sec.ww.np.dl.playstation.net",
    "account.sonyentertainmentnetwork.com", "store.playstation.com",
    "xbox.com", "xboxlive.com", "xboxservices.com", "xsts.auth.xboxlive.com",
    "user.auth.xboxlive.com", "title.auth.xboxlive.com", "multiplayer.xboxlive.com",
    "ea.com", "origin.com", "signin.ea.com", "accounts.ea.com",
    "gateway.ea.com", "river.data.ea.com", "utas.fut.ea.com", "fut-squad.ea.com",
    "activision.com", "callofduty.com", "demonware.net", "uno.demonware.net", "prod.demonware.net",
    "blizzard.com", "battle.net", "oauth.battle.net", "auth.battle.net",
    "ubisoft.com", "ubi.com", "connect.ubisoft.com",
    "epicgames.com", "ol.epicgames.com", "epicgames.org", "unrealengine.com",
    "fortnite.com", "rocketleague.com", "account-public-service-prod.ol.epicgames.com",
    "riotgames.com", "auth.riotgames.com", "playvalorant.com", "leagueoflegends.com",
    "nintendo.com", "nintendo.net", "discord.com", "discord.gg", "gateway.discord.gg",
    "adobe.com", "www.adobe.com", "adobe.io"
]
content = "    hosts {\n"
for d in domains:
    content += f"        {iran_ip} {d}\n"
content += "        fallthrough\n    }\n"
with open("/etc/coredns/gaming_rewrites.conf", "w") as f:
    f.write(content)
PYEOF
    python3 /tmp/gen_domains.py "$IRAN_IP"
    rm -f /tmp/gen_domains.py

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

    echo -e "${YELLOW}[5/5] Configuring HAProxy SNI forwarder & Customer Portal...${NC}"
    mkdir -p /etc/haproxy

    if [ -n "$CUSTOMER_DOMAIN" ]; then
        echo -e "${YELLOW}[*] Configuring SSL Certificate & Reverse Proxy for ${CUSTOMER_DOMAIN}...${NC}"
        mkdir -p /var/www/html /etc/nginx/conf.d

        cat > /etc/nginx/conf.d/customer_portal.conf << EOF
server {
    listen 80;
    server_name ${CUSTOMER_DOMAIN};
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
    location / {
        return 301 https://\$host\$request_uri;
    }
}
EOF
        systemctl restart nginx 2>/dev/null || true

        # Request SSL certificate
        certbot certonly --nginx -d "$CUSTOMER_DOMAIN" --non-interactive --agree-tos --register-unsafely-without-email 2>/dev/null || \
            certbot certonly --standalone -d "$CUSTOMER_DOMAIN" --non-interactive --agree-tos --register-unsafely-without-email 2>/dev/null || true

        if [ -d "/etc/letsencrypt/live/${CUSTOMER_DOMAIN}" ]; then
            cat > /etc/nginx/conf.d/customer_portal.conf << EOF
server {
    listen 80;
    server_name ${CUSTOMER_DOMAIN};
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
    location / {
        return 301 https://\$host\$request_uri;
    }
}

server {
    listen 127.0.0.1:8443 ssl;
    server_name ${CUSTOMER_DOMAIN};

    ssl_certificate /etc/letsencrypt/live/${CUSTOMER_DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${CUSTOMER_DOMAIN}/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }
}
EOF
            systemctl restart nginx 2>/dev/null || true
        fi

        # HAProxy SNI multiplexer: Customer Portal SNI -> local Nginx, Gaming SNI -> Kharej
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

    # Customer Web Portal Route (matches SNI)
    acl is_customer req.ssl_sni -i ${CUSTOMER_DOMAIN}
    acl is_customer req_ssl_sni -i ${CUSTOMER_DOMAIN}
    use_backend backend_customer if is_customer

    # Transparent Gaming Egress Route
    default_backend backend_kharej

backend backend_customer
    mode tcp
    server local_nginx 127.0.0.1:8443

backend backend_kharej
    mode tcp
    server kharej_gateway ${KHAREJ_IP}:${KHAREJ_PORT} check inter 3000
EOF

        # Deploy Python Customer Service
        mkdir -p /opt/smartdns-customer
        curl -sSL "https://raw.githubusercontent.com/Kayjz/DNS/main/panel/customer_server.py?v=$(date +%s)" -o /opt/smartdns-customer/customer_server.py
        chmod +x /opt/smartdns-customer/customer_server.py

        cat > /etc/systemd/system/smartdns-customer.service << SVC
[Unit]
Description=SmartDNS Customer Web Portal
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/smartdns-customer
Environment="PRIMARY_DNS=${IRAN_IP}"
Environment="KHAREJ_API=https://${KHAREJ_IP}:9443"
ExecStart=/usr/bin/python3 /opt/smartdns-customer/customer_server.py
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
SVC

        systemctl daemon-reload
        systemctl enable smartdns-customer
        systemctl restart smartdns-customer

    else
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
    default_backend backend_kharej

backend backend_kharej
    mode tcp
    server kharej_gateway ${KHAREJ_IP}:${KHAREJ_PORT} check inter 3000
EOF
    fi

    systemctl enable haproxy
    systemctl restart haproxy

    register_cli_command

    echo -e "\n${GREEN}================================================================${NC}"
    echo -e "${GREEN}  ? IRAN EDGE SMARTDNS NODE DEPLOYED SUCCESSFULLY!              ${NC}"
    echo -e "${GREEN}================================================================${NC}"
    echo -e "Primary DNS IP:      ${BOLD}${IRAN_IP}${NC}"
    echo -e "CoreDNS Status:      ${GREEN}Active (Port 53 UDP/TCP)${NC}"
    echo -e "HAProxy Forwarder:   ${GREEN}Forwarding to ${KHAREJ_IP}:${KHAREJ_PORT}${NC}"
    if [ -n "$CUSTOMER_DOMAIN" ]; then
        echo -e "Customer Portal:     ${BOLD}https://${CUSTOMER_DOMAIN}${NC} (Standard HTTPS Port 443 with SSL)"
    fi
    echo -e "Management Command:  Type ${CYAN}smart-dns${NC} anytime to open the menu"
    echo -e "----------------------------------------------------------------"
    echo -e "${YELLOW}Set your Console (PS5/Xbox/Switch/PC) DNS settings to:${NC}"
    echo -e "Primary DNS:   ${BOLD}${IRAN_IP}${NC}"
    echo -e "Secondary DNS: ${BOLD}1.1.1.1${NC} (or 8.8.8.8)\n"
    read -rp "Press Enter to return to main menu..."
}

# ==============================================================================
# MANAGEMENT CONSOLE MENU
# ==============================================================================
check_status() {
    print_banner
    echo -e "${BOLD}--- Service Health Status ---${NC}\n"
    CURRENT_ROLE=$(detect_state)

    if [ "$CURRENT_ROLE" == "iran" ]; then
        systemctl is-active --quiet coredns && echo -e "CoreDNS Service:        ${GREEN}[ACTIVE] (Port 53 listening)${NC}" || echo -e "CoreDNS Service:        ${RED}[FAILED]${NC}"
        systemctl is-active --quiet haproxy && echo -e "HAProxy Forwarder:      ${GREEN}[ACTIVE] (Port 443 listening)${NC}" || echo -e "HAProxy Forwarder:      ${RED}[FAILED]${NC}"
        if systemctl is-active --quiet smartdns-customer; then
            echo -e "Customer Web Portal:    ${GREEN}[ACTIVE] (Port 443 HTTPS)${NC}"
        fi

        KHAREJ_TARGET=$(grep -oP '(?<=server kharej_gateway )[\d.]+' /etc/haproxy/haproxy.cfg 2>/dev/null || echo "")
        if [ -n "$KHAREJ_TARGET" ]; then
            PING_RES=$(ping -c 3 -W 1 "$KHAREJ_TARGET" 2>/dev/null | grep -oP 'min/avg/max[^=]*=\s*[\d.]+/(\K[\d.]+)' || echo "Timeout")
            [ "$PING_RES" != "Timeout" ] && echo -e "Kharej Bridge Latency:  ${GREEN}${PING_RES} ms${NC} (${KHAREJ_TARGET})" || echo -e "Kharej Bridge Latency:  ${YELLOW}ICMP Blocked (TCP Active)${NC} (${KHAREJ_TARGET})"
        fi
    elif [ "$CURRENT_ROLE" == "kharej" ]; then
        systemctl is-active --quiet nginx && echo -e "Nginx SNI Egress:       ${GREEN}[ACTIVE] (Stream Gateway listening)${NC}" || echo -e "Nginx SNI Egress:       ${RED}[FAILED]${NC}"
        if systemctl is-active --quiet smartdns-admin; then
            echo -e "Admin Web Portal:       ${GREEN}[ACTIVE] (Master Admin Portal)${NC}"
        elif [ -f "/etc/nginx/conf.d/admin_panel.conf" ]; then
            echo -e "Admin Web Portal:       ${GREEN}[CONFIGURED]${NC}"
        fi
    fi

    echo -e "\n${BOLD}--- System Resources ---${NC}"
    echo -e "Memory Usage:           $(free -m | awk 'NR==2{printf "%s/%s MB (%.1f%%)\n", $3, $2, $3*100/$2}')"
    echo -e "CPU Load (1m, 5m):      $(awk '{print $1 ", " $2}' /proc/loadavg)"
    
    echo ""
    read -rp "Press Enter to return to menu..."
}

show_clients() {
    print_banner
    echo -e "${BOLD}--- Active Connected Clients & Traffic ---${NC}\n"
    CURRENT_ROLE=$(detect_state)

    if [ "$CURRENT_ROLE" == "iran" ]; then
        echo -e "${YELLOW}Active TCP Gaming Sessions to Port 443:${NC}"
        CONNS=$(ss -tn state established '( sport = :443 )' 2>/dev/null | awk 'NR>1 {print $4}' | cut -d: -f1 | sort | uniq -c | sort -nr || true)
        if [ -z "$CONNS" ]; then
            echo "  No active TCP sessions right now."
        else
            printf "  %-10s %-25s\n" "Sessions" "Client IP"
            echo "  -------------------------------------"
            echo "$CONNS" | while read -r count ip; do
                printf "  %-10s %-25s\n" "$count" "$ip"
            done
        fi

        echo -e "\n${YELLOW}Recent Unique DNS Queries:${NC}"
        DNS_IPS=$(journalctl -u coredns -n 200 --no-pager 2>/dev/null | grep -oP '(?<= - )\d+(\.\d+){3}(?=:\d+)' | sort | uniq -c | sort -nr | head -n 15 || true)
        if [ -z "$DNS_IPS" ]; then
            echo "  Waiting for new incoming queries..."
        else
            printf "  %-10s %-25s\n" "Queries" "Client IP"
            echo "  -------------------------------------"
            echo "$DNS_IPS" | while read -r count ip; do
                printf "  %-10s %-25s\n" "$count" "$ip"
            done
        fi
    elif [ "$CURRENT_ROLE" == "kharej" ]; then
        echo -e "${YELLOW}Active Streams from Iran Bridge:${NC}"
        ss -tn '( sport = :8443 )' 2>/dev/null | awk 'NR>1 {print $4}' | cut -d: -f1 | sort | uniq -c | sort -nr || echo "No active streams."
    fi

    echo ""
    read -rp "Press Enter to return to menu..."
}

view_logs() {
    print_banner
    echo -e "${BOLD}--- Live Log Stream (Press Ctrl+C to stop) ---${NC}\n"
    sleep 1
    CURRENT_ROLE=$(detect_state)
    [ "$CURRENT_ROLE" == "iran" ] && journalctl -u coredns -u haproxy -f -n 30
    [ "$CURRENT_ROLE" == "kharej" ] && journalctl -u nginx -f -n 30
}

add_domain() {
    print_banner
    echo -e "${BOLD}--- Add Domain to Interception List ---${NC}\n"
    read -rp "Enter domain to intercept (e.g. steamcommunity.com): " NEW_DOM
    NEW_DOM=$(echo "$NEW_DOM" | tr -d ' ' | tr '[:upper:]' '[:lower:]')

    [ -z "$NEW_DOM" ] && { echo -e "${RED}Invalid domain.${NC}"; sleep 1; return; }

    CONF="/etc/coredns/gaming_rewrites.conf"
    grep -q " ${NEW_DOM}$" "$CONF" 2>/dev/null && { echo -e "${YELLOW}Domain already added!${NC}"; sleep 2; return; }

    LOCAL_IP=$(grep -oP '(?<=hosts \{[\r\n\s]{1,100})\d+(\.\d+){3}' "$CONF" | head -n1 || echo "127.0.0.1")
    sed -i "/fallthrough/i \        ${LOCAL_IP} ${NEW_DOM}" "$CONF"
    systemctl restart coredns
    echo -e "\n${GREEN}[+] Domain '${NEW_DOM}' added and CoreDNS reloaded!${NC}"
    sleep 2
}

run_diagnostics() {
    print_banner
    echo -e "${BOLD}--- Running Self-Diagnostic Suite ---${NC}\n"
    CURRENT_ROLE=$(detect_state)

    if [ "$CURRENT_ROLE" == "iran" ]; then
        echo -e "${YELLOW}[1/2] Testing Split-Horizon DNS Resolution...${NC}"
        RES_GAME=$(dig @127.0.0.1 auth.api.sonyentertainmentnetwork.com +short 2>/dev/null || echo "FAILED")
        RES_CLEAN=$(dig @127.0.0.1 google.com +short 2>/dev/null | head -n1 || echo "FAILED")
        echo -e "  PSN Auth Domain:     ${GREEN}${RES_GAME}${NC}"
        echo -e "  Google Clean Domain: ${GREEN}${RES_CLEAN}${NC}"

        echo -e "\n${YELLOW}[2/2] Testing Egress Through Kharej...${NC}"
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --resolve adobe.com:443:127.0.0.1 https://adobe.com/ --connect-timeout 6 || echo "FAILED")
        if [ "$HTTP_CODE" == "200" ] || [ "$HTTP_CODE" == "301" ] || [ "$HTTP_CODE" == "302" ]; then
            echo -e "  Adobe TLS Egress:    ${GREEN}[PASSED] (HTTP Status: ${HTTP_CODE})${NC}"
        else
            echo -e "  Adobe TLS Egress:    ${RED}[FAILED / TIMEOUT (Status: ${HTTP_CODE})]${NC}"
        fi
    elif [ "$CURRENT_ROLE" == "kharej" ]; then
        ss -tlpn | grep -q "nginx" && echo -e "  Nginx Gateway: ${GREEN}[LISTENING AND READY]${NC}" || echo -e "  Nginx Gateway: ${RED}[NOT LISTENING]${NC}"
    fi

    echo ""
    read -rp "Press Enter to return to menu..."
}

restart_services() {
    print_banner
    echo -e "${YELLOW}[*] Restarting services...${NC}"
    CURRENT_ROLE=$(detect_state)
    if [ "$CURRENT_ROLE" == "iran" ]; then
        systemctl restart coredns haproxy 2>/dev/null || true
        systemctl restart nginx smartdns-customer 2>/dev/null || true
        echo -e "${GREEN}[+] CoreDNS, HAProxy, Nginx & Customer Portal restarted!${NC}"
    elif [ "$CURRENT_ROLE" == "kharej" ]; then
        systemctl restart nginx smartdns-admin 2>/dev/null || true
        echo -e "${GREEN}[+] Nginx & Master Admin Portal restarted!${NC}"
    fi
    sleep 2
}

uninstall_smartdns() {
    print_banner
    echo -e "${RED}${BOLD}================================================================${NC}"
    echo -e "${RED}${BOLD}                   COMPLETE UNINSTALLATION                      ${NC}"
    echo -e "${RED}${BOLD}================================================================${NC}\n"
    read -rp "Are you SURE you want to completely uninstall? (type 'yes'): " CONFIRM
    [ "$CONFIRM" != "yes" ] && { echo -e "${YELLOW}Aborted.${NC}"; sleep 1; return; }

    CURRENT_ROLE=$(detect_state)
    if [ "$CURRENT_ROLE" == "iran" ]; then
        systemctl stop coredns haproxy smartdns-customer nginx 2>/dev/null || true
        systemctl disable coredns haproxy smartdns-customer 2>/dev/null || true
        rm -f /etc/systemd/system/coredns.service /etc/systemd/system/smartdns-customer.service
        rm -rf /usr/local/bin/coredns /etc/coredns /etc/haproxy /opt/smartdns-customer /etc/nginx/conf.d/customer_portal.conf
        apt-get purge -y haproxy 2>/dev/null || true
        sed -i 's/DNSStubListener=no/#DNSStubListener=yes/' /etc/systemd/resolved.conf 2>/dev/null || true
        systemctl restart systemd-resolved 2>/dev/null || true
    elif [ "$CURRENT_ROLE" == "kharej" ]; then
        systemctl stop nginx smartdns-admin 2>/dev/null || true
        systemctl disable nginx smartdns-admin 2>/dev/null || true
        rm -f /etc/systemd/system/smartdns-admin.service
        rm -rf /etc/nginx /opt/smartdns-admin
        apt-get purge -y nginx nginx-common libnginx-mod-stream 2>/dev/null || true
    fi

    rm -f /etc/sysctl.d/99-smartdns-proxy.conf
    iptables -t mangle -F 2>/dev/null || true
    rm -f /usr/local/bin/smart-dns

    echo -e "\n${GREEN}[+] SmartDNS has been completely uninstalled from this server.${NC}"
    exit 0
}

# ==============================================================================
# MAIN MENU DISPATCHER
# ==============================================================================
main_menu() {
    while true; do
        print_banner
        STATE=$(detect_state)

        if [ "$STATE" == "iran" ]; then
            LOCAL_IP=$(get_public_ip)
            echo -e "Server Role: ${GREEN}${BOLD}Iran Edge Node (DNS Resolver + Proxy)${NC}"
            echo -e "Primary DNS: ${BOLD}${LOCAL_IP}${NC}"
            echo -e "${CYAN}--------------------------------------------------------------------------------${NC}"
            echo "  1) Check Status & Resource Usage"
            echo "  2) Show Connected Client IPs & Recent Queries"
            echo "  3) View Live Logs (Real-time Stream)"
            echo "  4) Add Domain to Unblock / Interception List"
            echo "  5) Run Diagnostics & Self-Test"
            echo "  6) Restart Services"
            echo "  7) Reinstall / Switch Server Role"
            echo "  8) Completely Uninstall SmartDNS"
            echo "  0) Exit"
            echo ""
            read -rp "Enter option [0-8]: " OPT
            case "$OPT" in
                1) check_status ;;
                2) show_clients ;;
                3) view_logs ;;
                4) add_domain ;;
                5) run_diagnostics ;;
                6) restart_services ;;
                7) install_iran_wizard ;;
                8) uninstall_smartdns ;;
                0) clear; exit 0 ;;
                *) echo -e "${RED}Invalid option.${NC}"; sleep 1 ;;
            esac

        elif [ "$STATE" == "kharej" ]; then
            LOCAL_IP=$(get_public_ip)
            echo -e "Server Role: ${MAGENTA}${BOLD}Kharej (Outside Iran) Egress Gateway${NC}"
            echo -e "Server IP:   ${BOLD}${LOCAL_IP}${NC}"
            echo -e "${CYAN}--------------------------------------------------------------------------------${NC}"
            echo "  1) Check Status & Resource Usage"
            echo "  2) Show Active Streams from Iran"
            echo "  3) View Live Logs"
            echo "  4) Run Diagnostics & Self-Test"
            echo "  5) Restart Nginx Gateway"
            echo "  6) Reinstall / Switch Server Role"
            echo "  7) Completely Uninstall SmartDNS"
            echo "  0) Exit"
            echo ""
            read -rp "Enter option [0-7]: " OPT
            case "$OPT" in
                1) check_status ;;
                2) show_clients ;;
                3) view_logs ;;
                4) run_diagnostics ;;
                5) restart_services ;;
                6) install_kharej_wizard ;;
                7) uninstall_smartdns ;;
                0) clear; exit 0 ;;
                *) echo -e "${RED}Invalid option.${NC}"; sleep 1 ;;
            esac

        else
            echo -e "Status: ${YELLOW}SmartDNS is NOT installed on this server yet.${NC}"
            echo -e "${CYAN}--------------------------------------------------------------------------------${NC}"
            echo "Please choose an installation option:"
            echo ""
            echo -e "  1) Install ${MAGENTA}${BOLD}Kharej (Outside Iran) Node + Admin Portal${NC} (Run this FIRST)"
            echo -e "  2) Install ${GREEN}${BOLD}Iran Edge Node + Customer Portal${NC} (Run this SECOND)"
            echo ""
            echo "  0) Exit"
            echo ""
            read -rp "Enter choice [0-2]: " INIT_CHOICE
            case "$INIT_CHOICE" in
                1) install_kharej_wizard ;;
                2) install_iran_wizard ;;
                0) clear; exit 0 ;;
                *) echo -e "${RED}Invalid choice.${NC}"; sleep 1 ;;
            esac
        fi
    done
}

main_menu
