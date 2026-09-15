#!/usr/bin/env bash
# ==============================================================================
# SMARTDNS & GAMING PROXY AUTOMATED BENCHMARK SUITE
# ==============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

DNS_SERVER="${1:-127.0.0.1}"

echo -e "${CYAN}================================================================${NC}"
echo -e "${CYAN}  SmartDNS & Gaming Tunnel Benchmark Suite                      ${NC}"
echo -e "${CYAN}  Testing Target DNS: ${DNS_SERVER}                             ${NC}"
echo -e "${CYAN}================================================================${NC}\n"

# Check dependencies
for cmd in dig curl ping bc; do
    if ! command -v "$cmd" &>/dev/null; then
        echo -e "${RED}[ERROR] Required utility '$cmd' is not installed. Run: apt-get install -y dnsutils curl iputils-ping bc${NC}"
        exit 1
    fi
done

# ------------------------------------------------------------------------------
# 1. DNS Resolution Speed & Interception Verification
# ------------------------------------------------------------------------------
echo -e "${YELLOW}[1/3] Testing DNS Resolution & Split-Horizon Rewrites...${NC}"
printf "%-40s | %-15s | %-12s | %-10s\n" "Domain" "Resolved IP" "Query Time" "Status"
echo "--------------------------------------------------------------------------------"

TEST_DOMAINS=(
    "auth.api.sonyentertainmentnetwork.com"
    "xsts.auth.xboxlive.com"
    "signin.ea.com"
    "prod.demonware.net"
    "auth.riotgames.com"
    "google.com"
    "cloudflare.com"
)

for domain in "${TEST_DOMAINS[@]}"; do
    START=$(date +%s%N)
    RES=$(dig @"$DNS_SERVER" +short +time=2 +tries=1 "$domain" 2>/dev/null | tail -n1 || true)
    END=$(date +%s%N)
    
    DIFF_MS=$(echo "scale=2; ($END - $START) / 1000000" | bc)
    
    if [ -n "$RES" ]; then
        STATUS="${GREEN}OK${NC}"
    else
        RES="FAILED"
        STATUS="${RED}ERR${NC}"
    fi
    
    printf "%-40s | %-15s | %-10s ms | " "$domain" "$RES" "$DIFF_MS"
    echo -e "$STATUS"
done
echo ""

# ------------------------------------------------------------------------------
# 2. Domestic vs International Network Latency & Packet Loss
# ------------------------------------------------------------------------------
echo -e "${YELLOW}[2/3] Measuring Latency & Packet Loss across Key Gateways...${NC}"
printf "%-30s | %-15s | %-12s | %-10s\n" "Endpoint" "Avg RTT" "Packet Loss" "Quality"
echo "--------------------------------------------------------------------------------"

PING_TARGETS=(
    "Cloudflare (1.1.1.1):1.1.1.1"
    "Google DNS (8.8.8.8):8.8.8.8"
    "Local Telecom (5.200.200.200):5.200.200.200"
)

for target in "${PING_TARGETS[@]}"; do
    LABEL=$(echo "$target" | cut -d: -f1)
    IP=$(echo "$target" | cut -d: -f2)
    
    PING_OUT=$(ping -c 5 -W 2 "$IP" 2>/dev/null || true)
    LOSS=$(echo "$PING_OUT" | grep -oP '\d+(?=% packet loss)' || echo "100")
    AVG=$(echo "$PING_OUT" | grep -oP 'min/avg/max[^=]*=\s*[\d.]+/(\K[\d.]+)' || echo "N/A")
    
    if [ "$LOSS" -eq 0 ]; then
        QUAL="${GREEN}EXCELLENT${NC}"
    elif [ "$LOSS" -lt 10 ]; then
        QUAL="${YELLOW}ACCEPTABLE${NC}"
    else
        QUAL="${RED}HIGH LOSS${NC}"
    fi
    
    printf "%-30s | %-12s ms | %-10s %% | " "$LABEL" "$AVG" "$LOSS"
    echo -e "$QUAL"
done
echo ""

# ------------------------------------------------------------------------------
# 3. End-to-End TLS / SNI Handshake Test
# ------------------------------------------------------------------------------
echo -e "${YELLOW}[3/3] Verifying End-to-End TLS Handshake (Simulating Console Client)...${NC}"

SNI_TARGETS=(
    "auth.api.sonyentertainmentnetwork.com"
    "xsts.auth.xboxlive.com"
    "signin.ea.com"
)

for sni in "${SNI_TARGETS[@]}"; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 4 -k --resolve "${sni}:443:${DNS_SERVER}" "https://${sni}/" || echo "FAILED")
    
    if [ "$HTTP_CODE" != "FAILED" ] && [ "$HTTP_CODE" != "000" ]; then
        echo -e "  [+] ${sni}: Handshake Successful (HTTP Status: ${GREEN}${HTTP_CODE}${NC})"
    else
        echo -e "  [-] ${sni}: ${RED}Connection failed or timed out${NC}"
    fi
done

echo -e "\n${GREEN}Benchmark complete!${NC}"
