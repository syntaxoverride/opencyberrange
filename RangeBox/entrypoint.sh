#!/bin/bash
# RangeBox Entrypoint
# Starts: Xvfb (virtual display) → XFCE4 (desktop) → x11vnc (VNC) → websockify (WebSocket bridge)
set -e

RESOLUTION="${RESOLUTION:-1280x800}"
DEPTH="${DEPTH:-16}"
VNC_PORT="${VNC_PORT:-5900}"
NOVNC_PORT="${NOVNC_PORT:-6080}"
DISPLAY_NUM="${DISPLAY_NUM:-1}"

export DISPLAY=":${DISPLAY_NUM}"
export HOME="/home/kali"

echo "[rangebox] Starting RangeBox..."
echo "[rangebox] Resolution: ${RESOLUTION}x${DEPTH}"
echo "[rangebox] VNC port: ${VNC_PORT}, noVNC port: ${NOVNC_PORT}"

# ── 1. Start virtual framebuffer ───────────────────────────────────────
echo "[rangebox] Starting Xvfb on display :${DISPLAY_NUM}..."
Xvfb "${DISPLAY}" -screen 0 "${RESOLUTION}x${DEPTH}" -ac +extension GLX +render -noreset &
XVFB_PID=$!

# Wait for X server to be ready
for i in $(seq 1 10); do
    if xdpyinfo -display "${DISPLAY}" >/dev/null 2>&1; then
        echo "[rangebox] Xvfb ready."
        break
    fi
    if [ "$i" -eq 10 ]; then
        echo "[rangebox] ERROR: Xvfb failed to start."
        exit 1
    fi
    sleep 0.5
done

# ── 1a. Block Docker gateway IPs to hide host services from nmap ──────
# Containers have NET_ADMIN; drop outbound to every .1 gateway on 10.x
# subnets.  A background loop re-applies when new interfaces appear
# (e.g. when the platform bridges us to a lab network after boot).
block_gateways() {
    if ! command -v iptables &>/dev/null; then
        echo "[rangebox] WARNING: iptables not found, skipping gateway block"
        return 0
    fi
    for iface in $(ip -4 addr show | grep 'inet 10\.' | awk '{print $2}'); do
        # OCR lab bridges put the gateway at .254 (docker_manager.py), not .1.
        # Blocking only .1 left the real gateway open, so the attack box could
        # reach the platform frontend and the Peer Manager on <subnet>.254.
        # Drop both the Docker-default .1 and the OCR .254.
        net="$(echo "$iface" | sed 's|\.[0-9]*/.*||')"
        for last in 1 254; do
            gw="${net}.${last}"
            iptables -C OUTPUT -d "$gw" -j DROP 2>/dev/null || \
                { iptables -A OUTPUT -d "$gw" -j DROP 2>/dev/null && \
                    echo "[rangebox] Blocked gateway $gw"; }
        done
    done
}
block_gateways || echo "[rangebox] WARNING: gateway blocking failed (non-fatal)"

# ── 1b. Start dnsmasq for clean reverse DNS ──────────────────────────
# Docker's embedded DNS (127.0.0.11) returns compose container names
# on PTR queries, leaking exercise slugs into nmap output. dnsmasq
# reads /etc/hosts and serves proper PTR records so reverse lookups
# return friendly names like plc1.masa.local.
_reload_dnsmasq() {
    [ -f /tmp/dnsmasq.pid ] && kill -HUP "$(cat /tmp/dnsmasq.pid)" 2>/dev/null
}
if command -v dnsmasq &>/dev/null; then
    DOCKER_DNS="127.0.0.11"
    cat > /tmp/dnsmasq.conf <<DNSCONF
listen-address=127.0.0.1
bind-interfaces
no-resolv
server=${DOCKER_DNS}
expand-hosts
no-negcache
# Do not forward reverse lookups of private (RFC1918) addresses upstream. Without
# this, PTR queries for lab targets were forwarded to Docker's embedded DNS,
# which answered with the compose container name and leaked the exercise slug
# into nmap output. bogus-priv answers those with NXDOMAIN instead, so reverse
# lookups of lab hosts return nothing rather than the slug.
bogus-priv
DNSCONF
    dnsmasq -C /tmp/dnsmasq.conf --pid-file=/tmp/dnsmasq.pid 2>/dev/null && {
        echo "nameserver 127.0.0.1" > /etc/resolv.conf
        echo "[rangebox] dnsmasq started, reverse DNS will use /etc/hosts"
    } || echo "[rangebox] WARNING: dnsmasq failed to start (non-fatal)"
fi

# Re-check gateways and reload dnsmasq every 30s for dynamically attached networks
( while true; do sleep 30; block_gateways 2>/dev/null; _reload_dnsmasq; done ) &

# ── 1c. Ensure XFCE preferred-apps config exists ─────────────────────
# Without this, exo-open --launch TerminalEmulator may open the browser.
mkdir -p "${HOME}/.config/xfce4"
if [ ! -f "${HOME}/.config/xfce4/helpers.rc" ]; then
    cat > "${HOME}/.config/xfce4/helpers.rc" <<'HELPERSRC'
TerminalEmulator=xfce4-terminal
WebBrowser=firefox-esr
FileManager=thunar
HELPERSRC
fi

# ── 2. Start D-Bus session (required by XFCE) ─────────────────────────
eval "$(dbus-launch --sh-syntax)" 2>/dev/null || true

# ── 3. Start XFCE4 desktop ────────────────────────────────────────────
echo "[rangebox] Starting XFCE4 desktop..."
startxfce4 &
XFCE_PID=$!

# Wait for desktop to initialize
sleep 3

# ── 4. Start VNC server ───────────────────────────────────────────────
# No password — authentication is handled by FastAPI's WebSocket proxy.
# The VNC port is only accessible within the Docker network.
echo "[rangebox] Starting x11vnc on port ${VNC_PORT}..."
x11vnc \
    -display "${DISPLAY}" \
    -forever \
    -shared \
    -rfbport "${VNC_PORT}" \
    -nopw \
    -xkb \
    -noxrecord \
    -noxfixes \
    -noxdamage \
    -cursor arrow \
    -nowf \
    -defer "${VNC_DEFER:-50}" \
    -wait "${VNC_WAIT:-30}" \
    -threads \
    &
X11VNC_PID=$!

# Wait for VNC server to bind
sleep 1

# ── 5. Start noVNC websockify bridge ──────────────────────────────────
# This is the main foreground process. When it exits, the container stops.
echo "[rangebox] Starting noVNC websockify on port ${NOVNC_PORT}..."
echo "[rangebox] ✓ RangeBox ready. Connect to http://localhost:${NOVNC_PORT}/vnc.html"

# Determine noVNC web directory
NOVNC_DIR="/usr/share/novnc"
if [ ! -f "${NOVNC_DIR}/vnc.html" ]; then
    NOVNC_DIR="/usr/share/novnc/utils/../"
fi

# Trap signals for graceful shutdown
cleanup() {
    echo "[rangebox] Shutting down..."
    kill "${X11VNC_PID}" 2>/dev/null || true
    kill "${XFCE_PID}" 2>/dev/null || true
    kill "${XVFB_PID}" 2>/dev/null || true
    exit 0
}
trap cleanup SIGTERM SIGINT

# Run websockify in foreground (keeps container alive)
websockify \
    --web "${NOVNC_DIR}" \
    "${NOVNC_PORT}" \
    "localhost:${VNC_PORT}"
