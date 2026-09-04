#!/bin/bash
# ============================================================================
# Contractor Dev Server Traffic Simulator
# Sends a mix of legitimate and suspicious traffic to the web server every
# few seconds. This simulates the rogue traffic the SOC team flagged.
# ============================================================================

# Wait for the network to settle and web server to come up
sleep 10

# Discover web server IP (offset .47 on our subnet)
SUBNET_PREFIX=$(ip -4 addr show | grep -oP '10\.\d+\.\d+' | head -1)
WEB_IP="${SUBNET_PREFIX}.47"

echo "Traffic generator starting: target=$WEB_IP"

while true; do
    # --- Legitimate traffic (HTTP) ---
    curl -s -o /dev/null --connect-timeout 2 "http://${WEB_IP}/" 2>/dev/null
    sleep 1

    # --- Legitimate traffic (HTTPS) ---
    curl -sk -o /dev/null --connect-timeout 2 "https://${WEB_IP}/" 2>/dev/null
    sleep 1

    # --- Suspicious: SSH brute-force attempt ---
    nc -z -w 1 "$WEB_IP" 22 2>/dev/null
    sleep 1

    # --- Legitimate traffic (HTTP) ---
    curl -s -o /dev/null --connect-timeout 2 "http://${WEB_IP}/index.html" 2>/dev/null
    sleep 1

    # --- Suspicious: MySQL database probe ---
    nc -z -w 1 "$WEB_IP" 3306 2>/dev/null
    sleep 1

    # --- Suspicious: Reverse shell callback ---
    nc -z -w 1 "$WEB_IP" 4444 2>/dev/null
    sleep 1

    # --- Legitimate traffic (HTTP) ---
    curl -s -o /dev/null --connect-timeout 2 "http://${WEB_IP}/" 2>/dev/null
    sleep 1

    # --- Suspicious: C2 beacon on 8080 ---
    nc -z -w 1 "$WEB_IP" 8080 2>/dev/null
    sleep 2
done
