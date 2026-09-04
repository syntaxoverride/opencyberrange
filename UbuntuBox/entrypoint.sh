#!/bin/bash
# UbuntuBox Entrypoint
# Starts: Xvfb (virtual display) → XFCE4 (desktop) → x11vnc (VNC) → websockify (WebSocket bridge)
set -e

RESOLUTION="${RESOLUTION:-1280x800}"
DEPTH="${DEPTH:-16}"
VNC_PORT="${VNC_PORT:-5900}"
NOVNC_PORT="${NOVNC_PORT:-6080}"
DISPLAY_NUM="${DISPLAY_NUM:-1}"

export DISPLAY=":${DISPLAY_NUM}"
export HOME="/home/student"

echo "[ubuntubox] Starting UbuntuBox..."
echo "[ubuntubox] Resolution: ${RESOLUTION}x${DEPTH}"
echo "[ubuntubox] VNC port: ${VNC_PORT}, noVNC port: ${NOVNC_PORT}"

# ── 0. Override shell prompt with platform username if provided ──────
if [ -n "${OCR_USERNAME}" ]; then
    echo "[ubuntubox] Setting prompt username to: ${OCR_USERNAME}"
    # Ubuntu uses bash — override PS1 in .bashrc
    cat >> "${HOME}/.bashrc" << BASHEOF

# OCR: show platform username in prompt
export PS1='\[\033[01;32m\]${OCR_USERNAME}@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ '
BASHEOF
fi

# ── 1. Start virtual framebuffer ───────────────────────────────────────
echo "[ubuntubox] Starting Xvfb on display :${DISPLAY_NUM}..."
Xvfb "${DISPLAY}" -screen 0 "${RESOLUTION}x${DEPTH}" -ac +extension GLX +render -noreset &
XVFB_PID=$!

# Wait for X server to be ready
for i in $(seq 1 10); do
    if xdpyinfo -display "${DISPLAY}" >/dev/null 2>&1; then
        echo "[ubuntubox] Xvfb ready."
        break
    fi
    if [ "$i" -eq 10 ]; then
        echo "[ubuntubox] ERROR: Xvfb failed to start."
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
        echo "[ubuntubox] WARNING: iptables not found, skipping gateway block"
        return 0
    fi
    for iface in $(ip -4 addr show | grep 'inet 10\.' | awk '{print $2}'); do
        gw="$(echo "$iface" | sed 's|\.[0-9]*/.*|.1|')"
        iptables -C OUTPUT -d "$gw" -j DROP 2>/dev/null || \
            iptables -A OUTPUT -d "$gw" -j DROP 2>/dev/null && \
            echo "[ubuntubox] Blocked gateway $gw"
    done
}
block_gateways || echo "[ubuntubox] WARNING: gateway blocking failed (non-fatal)"
# Re-check every 30s in the background for dynamically attached networks
( while true; do sleep 30; block_gateways 2>/dev/null; done ) &

# ── 1b. Ensure XFCE preferred-apps config exists ─────────────────────
mkdir -p "${HOME}/.config/xfce4"
if [ ! -f "${HOME}/.config/xfce4/helpers.rc" ]; then
    cat > "${HOME}/.config/xfce4/helpers.rc" <<'HELPERSRC'
TerminalEmulator=xfce4-terminal
WebBrowser=firefox
FileManager=thunar
HELPERSRC
fi

# ── 2. Start D-Bus session (required by XFCE) ─────────────────────────
eval "$(dbus-launch --sh-syntax)" 2>/dev/null || true

# ── 3. Start XFCE4 desktop ────────────────────────────────────────────
echo "[ubuntubox] Starting XFCE4 desktop..."
startxfce4 &
XFCE_PID=$!

# Wait for desktop to initialize
sleep 3

# ── 4. Start VNC server ───────────────────────────────────────────────
# No password — authentication is handled by FastAPI's WebSocket proxy.
# The VNC port is only accessible within the Docker network.
echo "[ubuntubox] Starting x11vnc on port ${VNC_PORT}..."
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
    &
X11VNC_PID=$!

# Wait for VNC server to bind
sleep 1

# ── 5. Start noVNC websockify bridge ──────────────────────────────────
# This is the main foreground process. When it exits, the container stops.
echo "[ubuntubox] Starting noVNC websockify on port ${NOVNC_PORT}..."
echo "[ubuntubox] Ready. Connect to http://localhost:${NOVNC_PORT}/vnc.html"

# Determine noVNC web directory
NOVNC_DIR="/usr/share/novnc"
if [ ! -f "${NOVNC_DIR}/vnc.html" ]; then
    NOVNC_DIR="/usr/share/novnc/utils/../"
fi

# Trap signals for graceful shutdown
cleanup() {
    echo "[ubuntubox] Shutting down..."
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
