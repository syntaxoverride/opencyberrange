#!/bin/bash
# ==============================================================================
# OpenCyberRange — Server Setup
# ==============================================================================
#
# Sets up EVERYTHING on a fresh Ubuntu/Debian server:
#   1. System packages (Docker, WireGuard, Python3, iptables-persistent)
#   2. IP forwarding
#   3. WireGuard VPN server (students connect directly to this server)
#   4. Peer Manager API (Flask app for dynamic peer registration)
#   5. VPN firewall rules (allow VPN traffic to reach Docker lab containers)
#   6. OpenCyberRange platform (backend, frontend, database, labs)
#
# USAGE:
#   sudo bash setup-range-server.sh              # Interactive menu
#   sudo bash setup-range-server.sh --install    # Full install (skip menu)
#   sudo bash setup-range-server.sh --fix        # Repair components
#   sudo bash setup-range-server.sh --status     # Check system health
#
# Or configure via environment variables before running:
#   export VPN_LISTEN_PORT=51820
#   export VPN_SERVER_ADDRESS="10.0.0.1/24"
#   export PEER_MANAGER_API_KEY="your-secret-key"
#   sudo -E bash setup-range-server.sh
#
# ==============================================================================

set -euo pipefail

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

# ── Configurable Defaults ─────────────────────────────────────────────────────
# Override any of these with environment variables before running.

VPN_ENABLED="${VPN_ENABLED:-true}"
DEPLOYMENT_MODE="${DEPLOYMENT_MODE:-internet}"
GENERATE_SELF_SIGNED="${GENERATE_SELF_SIGNED:-false}"
VPN_LISTEN_PORT="${VPN_LISTEN_PORT:-51820}"
VPN_SERVER_ADDRESS="${VPN_SERVER_ADDRESS:-10.0.0.1/24}"
VPN_INTERFACE="${VPN_INTERFACE:-wg0}"
LAB_CIDR="${LAB_CIDR:-10.100.0.0/16}"

PEER_MANAGER_PORT="${PEER_MANAGER_PORT:-5000}"
PEER_MANAGER_BIND="${PEER_MANAGER_BIND:-0.0.0.0}"
PEER_MANAGER_DIR="${PEER_MANAGER_DIR:-/opt/ocr-peer-manager}"

# Generate a random API key if not provided
PEER_MANAGER_API_KEY="${PEER_MANAGER_API_KEY:-}"

# Reuse existing API key if Peer Manager is already configured
if [ -z "$PEER_MANAGER_API_KEY" ] && [ -f "${PEER_MANAGER_DIR}/peer_manager.env" ]; then
    EXISTING_KEY=$(grep "^PEER_MANAGER_API_KEY=" "${PEER_MANAGER_DIR}/peer_manager.env" 2>/dev/null | cut -d'=' -f2) || true
    if [ -n "${EXISTING_KEY:-}" ]; then
        PEER_MANAGER_API_KEY="$EXISTING_KEY"
    fi
fi

# If still empty, generate a new one
if [ -z "$PEER_MANAGER_API_KEY" ]; then
    PEER_MANAGER_API_KEY="$(openssl rand -hex 32)"
fi

# Detect primary network interface for masquerade
PRIMARY_IFACE="${PRIMARY_IFACE:-$(ip route show default | awk '/default/ {print $5}' | head -1)}"

# Detect the real user (even under sudo)
if [ -n "${SUDO_USER:-}" ]; then
    REAL_USER="$SUDO_USER"
    REAL_HOME=$(getent passwd "$SUDO_USER" | cut -d: -f6)
else
    REAL_USER="$(whoami)"
    REAL_HOME="$HOME"
fi

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# Headless-friendly runtime dir (NOT ~/Desktop, absent on servers/cloud VMs).
# Override with OCR_PLATFORM_DIR; exported in phase_7 so install-platform.sh agrees.
PLATFORM_DIR="${OCR_PLATFORM_DIR:-$REAL_HOME/opencyberrange}"

# ── Helpers ───────────────────────────────────────────────────────────────────
log()   { echo -e "${GREEN}[+]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
err()   { echo -e "${RED}[✗]${NC} $1"; }
info()  { echo -e "${BLUE}[·]${NC} $1"; }
header(){ echo -e "\n${CYAN}═══ $1 ═══${NC}\n"; }

die() { err "$1"; exit 1; }

# Hand the git clone back to the invoking user. The install runs as root and
# writes into the clone (logs, build outputs, and the platform dir when it
# defaults under the clone), leaving root-owned files that would otherwise
# break the user's own `git pull` and edits. No-op when run as literal root.
restore_clone_ownership() {
    [ "$(id -u)" -eq 0 ] || return 0
    [ -n "${SUDO_USER:-}" ] || return 0
    chown -R "$REAL_USER":"$REAL_USER" "$REPO_DIR" 2>/dev/null || true
}

# ── Root check ────────────────────────────────────────────────────────────────
if [ "$(id -u)" -ne 0 ]; then
    die "This script must be run as root.  Use:  sudo bash $0"
fi

# ── Parse CLI arguments ──────────────────────────────────────────────────────
ACTION=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --install|-i)   ACTION="install"; shift ;;
        --update|-u)    ACTION="update"; shift ;;
        --platform|-p)  ACTION="platform"; shift ;;
        --fix|-f)       ACTION="fix"; shift ;;
        --status|-s)    ACTION="status"; shift ;;
        --help|-h)
            echo "Usage: sudo bash $0 [--install|--update|--platform|--fix|--status|--help]"
            echo ""
            echo "  --install, -i    Full server setup (all phases)"
            echo "  --update, -u     Update platform (pull changes, rebuild containers)"
            echo "  --platform, -p   Start / stop / restart platform containers"
            echo "  --fix, -f        Repair/restart specific components"
            echo "  --status, -s     Check system health"
            echo "  --help, -h       Show this help"
            echo "  (no args)        Interactive menu"
            exit 0
            ;;
        *) die "Unknown option: $1. Use --help for usage." ;;
    esac
done

# ── Banner ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${RED}${BOLD}     ██████╗  ██████╗██████╗ ${NC}"
echo -e "${RED}${BOLD}    ██╔═══██╗██╔════╝██╔══██╗${NC}"
echo -e "${YELLOW}${BOLD}    ██║   ██║██║     ██████╔╝${NC}"
echo -e "${GREEN}${BOLD}    ██║   ██║██║     ██╔══██╗${NC}"
echo -e "${CYAN}${BOLD}    ╚██████╔╝╚██████╗██║  ██║${NC}"
echo -e "${BLUE}${BOLD}     ╚═════╝  ╚═════╝╚═╝  ╚═╝${NC}"
echo ""
echo -e "${BOLD}${MAGENTA}    ╔═══════════════════════════════════════╗${NC}"
echo -e "${BOLD}${MAGENTA}    ║${NC}${BOLD}   O p e n C y b e r R a n g e         ${MAGENTA}║${NC}"
echo -e "${BOLD}${MAGENTA}    ║${NC}${DIM}   Server Setup                       ${MAGENTA}${BOLD}║${NC}"
echo -e "${BOLD}${MAGENTA}    ╚═══════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${DIM}──────────────────────────────────────────${NC}"
info "User               : ${BOLD}$REAL_USER${NC}"
info "Home               : ${BOLD}$REAL_HOME${NC}"
info "Repo               : ${BOLD}$REPO_DIR${NC}"
info "Platform dir       : ${BOLD}$PLATFORM_DIR${NC}"
info "VPN listen port    : ${BOLD}$VPN_LISTEN_PORT${NC}"
info "VPN server address : ${BOLD}$VPN_SERVER_ADDRESS${NC}"
info "Peer Manager port  : ${BOLD}${PEER_MANAGER_PORT}${NC} (internal API — not browser-accessible)"
info "Primary interface  : ${BOLD}$PRIMARY_IFACE${NC}"
echo -e "  ${DIM}──────────────────────────────────────────${NC}"
echo ""

# ==============================================================================
# PHASE FUNCTIONS
# ==============================================================================

phase_1_packages() {
    header "Phase 1 — System Packages"

    apt-get update -qq

    # Docker
    if command -v docker &>/dev/null; then
        log "Docker already installed ($(docker --version))"
    else
        info "Installing Docker..."
        apt-get install -y docker.io docker-compose-v2
        systemctl enable --now docker
        usermod -aG docker "$REAL_USER"
        log "Docker installed"
    fi

    # Docker Compose (v2 plugin check)
    if docker compose version &>/dev/null; then
        log "Docker Compose available"
    else
        warn "Docker Compose v2 not found — installing plugin"
        apt-get install -y docker-compose-v2 2>/dev/null || \
            apt-get install -y docker-compose-plugin 2>/dev/null || \
            die "Could not install Docker Compose v2"
    fi

    # Python3 (needed for Docker build and scripts)
    if command -v python3 &>/dev/null; then
        log "Python3 already installed"
    else
        apt-get install -y python3
    fi

    # WireGuard (always installed — required for user isolation)
    if command -v wg &>/dev/null; then
        log "WireGuard already installed"
    else
        info "Installing WireGuard..."
        apt-get install -y wireguard wireguard-tools
        log "WireGuard installed"
    fi

    # python3-venv (for Peer Manager API)
    apt-get install -y python3-venv 2>/dev/null || true
    log "python3-venv available"

    # iptables-persistent (non-interactive)
    if dpkg -l iptables-persistent &>/dev/null 2>&1; then
        log "iptables-persistent already installed"
    else
        info "Installing iptables-persistent..."
        DEBIAN_FRONTEND=noninteractive apt-get install -y iptables-persistent
        log "iptables-persistent installed"
    fi

    # Other useful tools
    for pkg in curl rsync openssl; do
        if ! command -v "$pkg" &>/dev/null; then
            apt-get install -y "$pkg"
        fi
    done

    log "All packages ready"
}

phase_2_ip_forwarding() {
    header "Phase 2 — IP Forwarding"

    if [ "$(cat /proc/sys/net/ipv4/ip_forward)" = "1" ]; then
        log "IP forwarding already enabled"
    else
        sysctl -w net.ipv4.ip_forward=1
        log "IP forwarding enabled (runtime)"
    fi

    # Make persistent
    if grep -q "^net.ipv4.ip_forward=1" /etc/sysctl.conf 2>/dev/null; then
        log "IP forwarding already persistent in sysctl.conf"
    else
        echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
        log "IP forwarding persisted to sysctl.conf"
    fi
}

prompt_deployment_scenario() {
    header "Deployment Scenario"

    echo ""
    echo -e "  ${BOLD}How will students access this server?${NC}"
    echo ""
    echo -e "    ${CYAN}1)${NC} ${BOLD}Local network only${NC}"
    echo -e "       Students are on the same network as this server"
    echo -e "       (classroom, school lab, school network)"
    echo -e "       VPN is installed for user isolation; HTTPS uses a self-signed certificate"
    echo ""
    echo -e "    ${CYAN}2)${NC} ${BOLD}Over the internet / cloud${NC}"
    echo -e "       Students connect remotely from home or other locations"
    echo -e "       Includes cloud servers (AWS, Azure, Hetzner, OVH, etc.)"
    echo -e "       VPN is installed; optional WSTunnel for Cloudflare deployments"
    echo ""
    read -rp "  Select [1-2]: " scenario_choice
    case "$scenario_choice" in
        1)
            DEPLOYMENT_MODE="local"
            GENERATE_SELF_SIGNED=true
            log "Local network mode — VPN + self-signed HTTPS"
            info "WireGuard VPN will be installed for user isolation."
            info "The VPN endpoint will use this server's LAN IP address."
            info "A self-signed TLS certificate will be generated for HTTPS."
            ;;
        *)
            DEPLOYMENT_MODE="internet"
            log "Internet / cloud mode — VPN + public endpoint"
            info "WireGuard VPN will be installed with a public-facing endpoint."
            info ""
            info "If deploying to a cloud provider (AWS, Azure, Hetzner, OVH, etc.),"
            info "open the following ports in your provider's security group or firewall:"
            info "  • 443/TCP   — HTTPS (platform web interface)"
            info "  • 51820/UDP — WireGuard VPN"
            info "  • 5555/TCP  — WSTunnel (only if using Cloudflare Tunnel)"
            ;;
    esac
}

phase_3_wireguard() {
    header "Phase 3 — WireGuard VPN Server"

    local WG_CONF="/etc/wireguard/${VPN_INTERFACE}.conf"
    local WG_KEYDIR="/etc/wireguard"

    # Generate server keys if they don't exist
    if [ -f "${WG_KEYDIR}/server_private.key" ] && [ -f "${WG_KEYDIR}/server_public.key" ]; then
        log "Server keys already exist"
        SERVER_PRIVKEY=$(cat "${WG_KEYDIR}/server_private.key")
        SERVER_PUBKEY=$(cat "${WG_KEYDIR}/server_public.key")
    else
        info "Generating server keypair..."
        # Contain the restrictive umask to key generation only. Left process-wide
        # it leaked into the later frontend image build, where the copied dist
        # assets (logo, JS) inherited 0600 and nginx served them 403 until an
        # Update rebuilt the image.
        ( umask 077; wg genkey | tee "${WG_KEYDIR}/server_private.key" | wg pubkey > "${WG_KEYDIR}/server_public.key" )
        chmod 600 "${WG_KEYDIR}/server_private.key"
        SERVER_PRIVKEY=$(cat "${WG_KEYDIR}/server_private.key")
        SERVER_PUBKEY=$(cat "${WG_KEYDIR}/server_public.key")
        log "Server keys generated"
    fi

    if [ -f "$WG_CONF" ]; then
        warn "WireGuard config already exists at $WG_CONF — skipping generation"
        warn "To regenerate, delete $WG_CONF and re-run this script"
    else
        # Build config
        cat > "$WG_CONF" <<EOF
# OpenCyberRange — WireGuard VPN Server
# Generated: $(date -Iseconds)
#
# Server public key: ${SERVER_PUBKEY}
# Students connect directly to this server to access lab containers.

[Interface]
PrivateKey = ${SERVER_PRIVKEY}
Address = ${VPN_SERVER_ADDRESS}
ListenPort = ${VPN_LISTEN_PORT}

# iptables rules: allow only VPN <-> lab traffic, block everything else
PostUp   = iptables -I FORWARD 1 -i %i -d ${LAB_CIDR} -j ACCEPT; iptables -I FORWARD 1 -o %i -s ${LAB_CIDR} -j ACCEPT; iptables -t nat -I POSTROUTING 1 -s ${LAB_CIDR} -o %i -j RETURN; iptables -t raw -I PREROUTING 1 -i %i -d ${LAB_CIDR} -j ACCEPT; iptables -A FORWARD -i %i -j DROP
PostDown = iptables -D FORWARD -i %i -d ${LAB_CIDR} -j ACCEPT; iptables -D FORWARD -o %i -s ${LAB_CIDR} -j ACCEPT; iptables -t nat -D POSTROUTING -s ${LAB_CIDR} -o %i -j RETURN; iptables -t raw -D PREROUTING -i %i -d ${LAB_CIDR} -j ACCEPT; iptables -D FORWARD -i %i -j DROP

# ── Student Peers ─────────────────────────────────────────────────────────────
# Student peers are managed dynamically by the Peer Manager API.
# Do not add them manually.
EOF

        chmod 600 "$WG_CONF"
        log "WireGuard config written to $WG_CONF"
    fi

    # Enable and start WireGuard
    systemctl enable "wg-quick@${VPN_INTERFACE}" 2>/dev/null || true
    if systemctl is-active --quiet "wg-quick@${VPN_INTERFACE}"; then
        log "WireGuard ${VPN_INTERFACE} already running"
    else
        info "Starting WireGuard ${VPN_INTERFACE}..."
        systemctl start "wg-quick@${VPN_INTERFACE}" || warn "Could not start WireGuard (check config)"
    fi
}

phase_4_peer_manager() {
    header "Phase 4 — Peer Manager API"

    mkdir -p "$PEER_MANAGER_DIR"

    # Create Python virtual environment and install Flask
    if [ ! -d "${PEER_MANAGER_DIR}/venv" ]; then
        info "Creating Python venv for Peer Manager..."
        python3 -m venv "${PEER_MANAGER_DIR}/venv"
    fi
    "${PEER_MANAGER_DIR}/venv/bin/pip" install --quiet flask
    log "Flask installed in venv"

    # Write the Peer Manager Flask API
    cat > "${PEER_MANAGER_DIR}/peer_manager.py" <<'PYEOF'
#!/usr/bin/env python3
"""
OCR Peer Manager — WireGuard Peer Management API

A lightweight Flask API that manages WireGuard peers dynamically.
Used by the OpenCyberRange backend to register/remove student VPN peers.

Endpoints:
  GET    /peers              — List all peers
  POST   /peers              — Add a peer        { "public_key": "...", "allowed_ips": "..." }
  DELETE  /peers/<public_key> — Remove a peer

Authentication: X-API-Key header
"""

import json
import os
import subprocess
import sys
import logging
from datetime import datetime, timezone
from flask import Flask, request, jsonify

app = Flask(__name__)

API_KEY = os.environ.get("PEER_MANAGER_API_KEY", "")
WG_INTERFACE = os.environ.get("WG_INTERFACE", "wg0")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("peer-manager")


# ── Auth ──────────────────────────────────────────────────────────────────────

def check_auth():
    """Verify the X-API-Key header."""
    if not API_KEY:
        return  # No key configured — allow all (dev mode)
    key = request.headers.get("X-API-Key", "")
    if key != API_KEY:
        return jsonify({"error": "unauthorized"}), 401


# ── Helpers ───────────────────────────────────────────────────────────────────

def wg_show():
    """Parse `wg show <iface> dump` into a list of peer dicts."""
    try:
        result = subprocess.run(
            ["wg", "show", WG_INTERFACE, "dump"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            log.error("wg show failed: %s", result.stderr.strip())
            return []

        lines = result.stdout.strip().split("\n")
        if len(lines) < 2:
            return []

        peers = []
        # First line is the interface itself; remaining are peers
        for line in lines[1:]:
            parts = line.split("\t")
            if len(parts) < 8:
                continue
            peer = {
                "public_key": parts[0],
                "preshared_key": parts[1] if parts[1] != "(none)" else None,
                "endpoint": parts[2] if parts[2] != "(none)" else None,
                "allowed_ips": parts[3],
                "last_handshake": int(parts[4]) if parts[4] != "0" else None,
                "rx_bytes": int(parts[5]),
                "tx_bytes": int(parts[6]),
                "persistent_keepalive": parts[7] if parts[7] != "off" else None,
            }
            # Add human-readable handshake time
            if peer["last_handshake"]:
                peer["last_handshake_time"] = datetime.fromtimestamp(
                    peer["last_handshake"], tz=timezone.utc
                ).isoformat()
            peers.append(peer)
        return peers

    except Exception as e:
        log.exception("Error reading WireGuard state: %s", e)
        return []


def wg_add_peer(public_key: str, allowed_ips: str):
    """Add a peer via `wg set`."""
    cmd = ["wg", "set", WG_INTERFACE, "peer", public_key, "allowed-ips", allowed_ips]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
    if result.returncode != 0:
        raise RuntimeError(f"wg set failed: {result.stderr.strip()}")
    # Persist to config file
    _save_config()


def wg_remove_peer(public_key: str):
    """Remove a peer via `wg set ... remove`."""
    cmd = ["wg", "set", WG_INTERFACE, "peer", public_key, "remove"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
    if result.returncode != 0:
        raise RuntimeError(f"wg set remove failed: {result.stderr.strip()}")
    _save_config()


def _save_config():
    """Persist current running WireGuard config to the conf file."""
    try:
        result = subprocess.run(
            ["wg-quick", "save", WG_INTERFACE],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            log.warning("wg-quick save failed: %s", result.stderr.strip())
    except Exception as e:
        log.warning("Could not save WireGuard config: %s", e)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.before_request
def before_request():
    if request.path == "/health":
        return  # health check is unauthenticated
    auth_result = check_auth()
    if auth_result is not None:
        return auth_result


@app.route("/peers", methods=["GET"])
def list_peers():
    peers = wg_show()
    return jsonify({"peers": peers, "count": len(peers)})


@app.route("/peers", methods=["POST"])
def add_peer():
    data = request.get_json(force=True)
    public_key = data.get("public_key", "").strip()
    allowed_ips = data.get("allowed_ips", "").strip()

    if not public_key or not allowed_ips:
        return jsonify({"error": "public_key and allowed_ips required"}), 400

    try:
        wg_add_peer(public_key, allowed_ips)
        log.info("Added peer %s... with allowed_ips %s", public_key[:20], allowed_ips)
        return jsonify({"status": "ok", "public_key": public_key, "allowed_ips": allowed_ips}), 201
    except RuntimeError as e:
        log.error("Failed to add peer: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route("/peers/<path:public_key>", methods=["DELETE"])
def remove_peer(public_key):
    public_key = public_key.strip()
    if not public_key:
        return jsonify({"error": "public_key required"}), 400

    # Check peer exists
    peers = wg_show()
    exists = any(p["public_key"] == public_key for p in peers)
    if not exists:
        return jsonify({"error": "peer not found"}), 404

    try:
        wg_remove_peer(public_key)
        log.info("Removed peer %s...", public_key[:20])
        return jsonify({"status": "ok", "public_key": public_key})
    except RuntimeError as e:
        log.error("Failed to remove peer: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route("/firewall/ensure", methods=["POST"])
def ensure_firewall():
    """Ensure iptables rules allow VPN traffic to reach lab containers.
    Docker adds DROP rules that block traffic from non-bridge interfaces.
    These rules must be inserted before Docker's rules."""
    vpn_iface = WG_INTERFACE
    lab_cidr = os.environ.get("LAB_CIDR", "10.100.0.0/16")
    results = []

    rules = [
        # nat PREROUTING: exempt lab traffic from port 80/443 REDIRECT rules
        # (wstunnel REDIRECT rules catch all wg0 port 80/443 traffic;
        #  lab container traffic must bypass them)
        {"check": ["-t", "nat", "-C", "PREROUTING", "-i", vpn_iface, "-d", lab_cidr, "-p", "tcp", "--dport", "80", "-j", "ACCEPT"],
         "add":   ["-t", "nat", "-I", "PREROUTING", "1", "-i", vpn_iface, "-d", lab_cidr, "-p", "tcp", "--dport", "80", "-j", "ACCEPT"],
         "desc":  f"nat PREROUTING ACCEPT {vpn_iface} -> {lab_cidr} tcp/80 (bypass REDIRECT)"},
        {"check": ["-t", "nat", "-C", "PREROUTING", "-i", vpn_iface, "-d", lab_cidr, "-p", "tcp", "--dport", "443", "-j", "ACCEPT"],
         "add":   ["-t", "nat", "-I", "PREROUTING", "1", "-i", vpn_iface, "-d", lab_cidr, "-p", "tcp", "--dport", "443", "-j", "ACCEPT"],
         "desc":  f"nat PREROUTING ACCEPT {vpn_iface} -> {lab_cidr} tcp/443 (bypass REDIRECT)"},
        # raw PREROUTING: bypass Docker per-network DROP rules
        {"check": ["-t", "raw", "-C", "PREROUTING", "-i", vpn_iface, "-d", lab_cidr, "-j", "ACCEPT"],
         "add":   ["-t", "raw", "-I", "PREROUTING", "1", "-i", vpn_iface, "-d", lab_cidr, "-j", "ACCEPT"],
         "desc":  f"raw PREROUTING ACCEPT {vpn_iface} -> {lab_cidr}"},
        # FORWARD inbound: VPN -> lab containers
        {"check": ["-C", "FORWARD", "-i", vpn_iface, "-d", lab_cidr, "-j", "ACCEPT"],
         "add":   ["-I", "FORWARD", "1", "-i", vpn_iface, "-d", lab_cidr, "-j", "ACCEPT"],
         "desc":  f"FORWARD ACCEPT {vpn_iface} -> {lab_cidr}"},
        # FORWARD outbound: lab containers -> VPN (return traffic)
        {"check": ["-C", "FORWARD", "-o", vpn_iface, "-s", lab_cidr, "-j", "ACCEPT"],
         "add":   ["-I", "FORWARD", "1", "-o", vpn_iface, "-s", lab_cidr, "-j", "ACCEPT"],
         "desc":  f"FORWARD ACCEPT {lab_cidr} -> {vpn_iface}"},
        # nat POSTROUTING: prevent Docker auto-MASQUERADE from rewriting
        # container source IPs on return traffic through VPN
        {"check": ["-t", "nat", "-C", "POSTROUTING", "-s", lab_cidr, "-o", vpn_iface, "-j", "RETURN"],
         "add":   ["-t", "nat", "-I", "POSTROUTING", "1", "-s", lab_cidr, "-o", vpn_iface, "-j", "RETURN"],
         "desc":  f"nat POSTROUTING RETURN {lab_cidr} -> {vpn_iface} (skip MASQUERADE)"},
        # DROP all other VPN traffic (defense-in-depth — blocks home network access)
        {"check": ["-C", "FORWARD", "-i", vpn_iface, "-j", "DROP"],
         "add":   ["-A", "FORWARD", "-i", vpn_iface, "-j", "DROP"],
         "desc":  f"FORWARD DROP all other {vpn_iface} traffic"},
    ]

    for rule in rules:
        try:
            check = subprocess.run(["iptables"] + rule["check"],
                                   capture_output=True, text=True, timeout=5)
            if check.returncode != 0:
                add = subprocess.run(["iptables"] + rule["add"],
                                     capture_output=True, text=True, timeout=5)
                if add.returncode == 0:
                    log.info("Added iptables rule: %s", rule["desc"])
                    results.append({"rule": rule["desc"], "action": "added"})
                else:
                    log.warning("Failed to add rule %s: %s", rule["desc"], add.stderr.strip())
                    results.append({"rule": rule["desc"], "action": "failed", "error": add.stderr.strip()})
            else:
                results.append({"rule": rule["desc"], "action": "exists"})
        except Exception as e:
            results.append({"rule": rule["desc"], "action": "error", "error": str(e)})

    return jsonify({"status": "ok", "rules": results})


@app.route("/firewall/audit", methods=["GET"])
def firewall_audit():
    """Audit nat PREROUTING chain for correct VPN rule ordering.

    Checks that ACCEPT rules for lab traffic on ports 80/443 appear
    before any REDIRECT rules that would capture that traffic.
    """
    import re as regex

    vpn_iface = WG_INTERFACE
    lab_cidr = os.environ.get("LAB_CIDR", "10.100.0.0/16")

    try:
        result = subprocess.run(
            ["iptables", "-t", "nat", "-S", "PREROUTING"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return jsonify({"status": "error", "checks": [], "rules": [],
                            "raw_output": result.stderr.strip()}), 500
        raw_output = result.stdout.strip()
    except Exception as e:
        return jsonify({"status": "error", "checks": [],
                        "rules": [], "raw_output": str(e)}), 500

    parsed_rules = []
    for line_num, line in enumerate(raw_output.split("\n"), 1):
        line = line.strip()
        if not line or line.startswith("-P"):
            continue
        rule = {"line": line_num, "raw": line}
        target_m = regex.search(r"-j\s+(\S+)", line)
        rule["target"] = target_m.group(1) if target_m else "unknown"
        proto_m = regex.search(r"-p\s+(\S+)", line)
        rule["proto"] = proto_m.group(1) if proto_m else "all"
        iface_m = regex.search(r"-i\s+(\S+)", line)
        rule["iface"] = iface_m.group(1) if iface_m else "*"
        dst_m = regex.search(r"-d\s+(\S+)", line)
        rule["destination"] = dst_m.group(1) if dst_m else "0.0.0.0/0"
        dport_m = regex.search(r"--dport\s+(\d+)", line)
        rule["dport"] = int(dport_m.group(1)) if dport_m else None
        redir_m = regex.search(r"--to-ports?\s+(\d+)", line)
        rule["redir_to"] = int(redir_m.group(1)) if redir_m else None
        parsed_rules.append(rule)

    checks = []
    overall = "ok"
    lab_prefix = lab_cidr.split("/")[0].rsplit(".", 1)[0]

    for port in [80, 443]:
        accept_lines = [r["line"] for r in parsed_rules
                        if r["target"] == "ACCEPT" and r["iface"] == vpn_iface
                        and r.get("dport") == port
                        and r.get("destination", "").startswith(lab_prefix)]
        redirect_lines = [r["line"] for r in parsed_rules
                          if r["target"] == "REDIRECT" and r["iface"] == vpn_iface
                          and r.get("dport") == port]

        if not accept_lines and redirect_lines:
            checks.append({"name": f"Lab traffic ACCEPT before REDIRECT (port {port})",
                           "status": "error",
                           "detail": f"No ACCEPT rule for {lab_cidr} port {port} — REDIRECT at line {redirect_lines[0]} captures all traffic"})
            overall = "error"
        elif accept_lines and redirect_lines:
            if min(accept_lines) < min(redirect_lines):
                checks.append({"name": f"Lab traffic ACCEPT before REDIRECT (port {port})",
                               "status": "ok",
                               "detail": f"ACCEPT at line {min(accept_lines)}, REDIRECT at line {min(redirect_lines)}"})
            else:
                checks.append({"name": f"Lab traffic ACCEPT before REDIRECT (port {port})",
                               "status": "error",
                               "detail": f"REDIRECT at line {min(redirect_lines)} before ACCEPT at line {min(accept_lines)}"})
                overall = "error"
        elif not redirect_lines:
            checks.append({"name": f"Lab traffic ACCEPT before REDIRECT (port {port})",
                           "status": "ok", "detail": f"No REDIRECT rule for port {port} (no conflict)"})

    lab_accept_ports = {r["dport"] for r in parsed_rules
                        if r["target"] == "ACCEPT" and r["iface"] == vpn_iface
                        and r.get("destination", "").startswith(lab_prefix)
                        and r.get("dport") in (80, 443)}
    if lab_accept_ports == {80, 443}:
        checks.append({"name": "Lab CIDR ACCEPT rules present", "status": "ok",
                        "detail": f"Found ACCEPT for {lab_cidr} on ports 80, 443"})
    else:
        missing = {80, 443} - lab_accept_ports
        checks.append({"name": "Lab CIDR ACCEPT rules present", "status": "error",
                        "detail": f"Missing ACCEPT for {lab_cidr} on port(s): {', '.join(str(p) for p in sorted(missing))}"})
        overall = "error"

    return jsonify({
        "status": overall, "checks": checks,
        "rules": [r for r in parsed_rules if r.get("iface") == vpn_iface or r["target"] in ("DOCKER", "REDIRECT")],
        "raw_output": raw_output
    })


@app.route("/port-test", methods=["POST"])
def port_test():
    """Test TCP connectivity from the host to a container IP:port.

    Runs on the host so it has direct routing to all lab networks (10.100.0.0/16).
    The backend container cannot reach lab IPs directly, so it proxies through here.
    """
    import socket as sock
    import ipaddress

    data = request.get_json(force=True) or {}
    ip = str(data.get("ip", "")).strip()
    port = data.get("port")

    # Validate IP is in lab CIDR
    try:
        addr = ipaddress.ip_address(ip)
        lab_net = ipaddress.ip_network(os.environ.get("LAB_CIDR", "10.100.0.0/16"))
        if addr not in lab_net:
            return jsonify({"error": "IP must be in the lab network"}), 400
    except ValueError:
        return jsonify({"error": "Invalid IP address"}), 400

    if not isinstance(port, int) or port < 1 or port > 65535:
        return jsonify({"error": "Port must be between 1 and 65535"}), 400

    try:
        s = sock.socket(sock.AF_INET, sock.SOCK_STREAM)
        s.settimeout(3)
        result = s.connect_ex((ip, int(port)))
        s.close()
        if result == 0:
            return jsonify({"status": "open", "ip": ip, "port": port})
        else:
            return jsonify({"status": "closed", "ip": ip, "port": port,
                            "detail": f"connect_ex returned {result}"})
    except sock.timeout:
        return jsonify({"status": "timeout", "ip": ip, "port": port})
    except Exception as e:
        return jsonify({"status": "error", "ip": ip, "port": port, "detail": str(e)})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "interface": WG_INTERFACE})


if __name__ == "__main__":
    bind = os.environ.get("PEER_MANAGER_BIND", "0.0.0.0")
    port = int(os.environ.get("PEER_MANAGER_PORT", "5000"))
    log.info("Peer Manager starting on %s:%d (interface: %s)", bind, port, WG_INTERFACE)
    app.run(host=bind, port=port)
PYEOF

    chmod 644 "${PEER_MANAGER_DIR}/peer_manager.py"
    log "Peer Manager API written to ${PEER_MANAGER_DIR}/peer_manager.py"

    # Write env file for Peer Manager
    cat > "${PEER_MANAGER_DIR}/peer_manager.env" <<EOF
PEER_MANAGER_API_KEY=${PEER_MANAGER_API_KEY}
PEER_MANAGER_BIND=${PEER_MANAGER_BIND}
PEER_MANAGER_PORT=${PEER_MANAGER_PORT}
WG_INTERFACE=${VPN_INTERFACE}
LAB_CIDR=${LAB_CIDR}
EOF
    chmod 600 "${PEER_MANAGER_DIR}/peer_manager.env"
    log "Peer Manager env written to ${PEER_MANAGER_DIR}/peer_manager.env"

    # Create systemd service for Peer Manager
    cat > /etc/systemd/system/ocr-peer-manager.service <<EOF
[Unit]
Description=OpenCyberRange WireGuard Peer Management API
After=network.target wg-quick@${VPN_INTERFACE}.service
Wants=wg-quick@${VPN_INTERFACE}.service

[Service]
Type=simple
EnvironmentFile=${PEER_MANAGER_DIR}/peer_manager.env
ExecStart=${PEER_MANAGER_DIR}/venv/bin/python ${PEER_MANAGER_DIR}/peer_manager.py
Restart=on-failure
RestartSec=5

# Security hardening
NoNewPrivileges=false
ProtectSystem=strict
ReadWritePaths=/etc/wireguard

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable ocr-peer-manager.service
    systemctl restart ocr-peer-manager.service
    log "ocr-peer-manager.service installed and started"
}

phase_5_firewall_rules() {
    header "Phase 5 — VPN Firewall Rules"

    # Apply the firewall rules right now
    _apply_vpn_firewall() {
        local iface="$1"
        local cidr="$2"

        # Raw PREROUTING — bypass Docker per-network DROP rules
        if ! iptables -t raw -C PREROUTING -i "$iface" -d "$cidr" -j ACCEPT 2>/dev/null; then
            iptables -t raw -I PREROUTING 1 -i "$iface" -d "$cidr" -j ACCEPT
            log "raw PREROUTING ACCEPT: ${iface} → ${cidr}"
        else
            info "raw PREROUTING rule already present"
        fi

        # FORWARD inbound: VPN → lab containers
        if ! iptables -C FORWARD -i "$iface" -d "$cidr" -j ACCEPT 2>/dev/null; then
            iptables -I FORWARD 1 -i "$iface" -d "$cidr" -j ACCEPT
            log "FORWARD ACCEPT: ${iface} → ${cidr}"
        else
            info "FORWARD inbound rule already present"
        fi

        # FORWARD outbound: lab containers → VPN (return traffic)
        if ! iptables -C FORWARD -o "$iface" -s "$cidr" -j ACCEPT 2>/dev/null; then
            iptables -I FORWARD 1 -o "$iface" -s "$cidr" -j ACCEPT
            log "FORWARD ACCEPT: ${cidr} → ${iface}"
        else
            info "FORWARD outbound rule already present"
        fi

        # NAT POSTROUTING — prevent Docker's auto-MASQUERADE from rewriting
        # source IPs on return traffic going back through the VPN tunnel.
        # Without this, Docker rewrites container IPs (10.100.x.x) to the
        # server's wg0 IP (10.0.0.1), so nmap/SSH see responses from the
        # wrong host and report "host down."
        if ! iptables -t nat -C POSTROUTING -s "$cidr" -o "$iface" -j RETURN 2>/dev/null; then
            iptables -t nat -I POSTROUTING 1 -s "$cidr" -o "$iface" -j RETURN
            log "nat POSTROUTING RETURN: ${cidr} → ${iface} (skip MASQUERADE)"
        else
            info "nat POSTROUTING RETURN rule already present"
        fi

        # DROP all other VPN traffic (defense-in-depth — blocks home network access)
        if ! iptables -C FORWARD -i "$iface" -j DROP 2>/dev/null; then
            iptables -A FORWARD -i "$iface" -j DROP
            log "FORWARD DROP: all other traffic from ${iface}"
        else
            info "FORWARD DROP rule already present"
        fi
    }

    _apply_vpn_firewall "$VPN_INTERFACE" "$LAB_CIDR"

    # Persist via netfilter-persistent
    netfilter-persistent save 2>/dev/null || warn "Could not save iptables rules via netfilter-persistent"

    # Also create a systemd oneshot service that re-applies after Docker messes with iptables
    local SYSTEMD_UNIT="/etc/systemd/system/ocr-vpn-firewall.service"
    cat > "$SYSTEMD_UNIT" <<EOF
[Unit]
Description=OpenCyberRange VPN Firewall Rules
After=docker.service wg-quick@${VPN_INTERFACE}.service
Wants=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/bash -c ' \\
    iptables -t raw -C PREROUTING -i ${VPN_INTERFACE} -d ${LAB_CIDR} -j ACCEPT 2>/dev/null || \\
        iptables -t raw -I PREROUTING 1 -i ${VPN_INTERFACE} -d ${LAB_CIDR} -j ACCEPT; \\
    iptables -C FORWARD -i ${VPN_INTERFACE} -d ${LAB_CIDR} -j ACCEPT 2>/dev/null || \\
        iptables -I FORWARD 1 -i ${VPN_INTERFACE} -d ${LAB_CIDR} -j ACCEPT; \\
    iptables -C FORWARD -o ${VPN_INTERFACE} -s ${LAB_CIDR} -j ACCEPT 2>/dev/null || \\
        iptables -I FORWARD 1 -o ${VPN_INTERFACE} -s ${LAB_CIDR} -j ACCEPT; \\
    iptables -t nat -C POSTROUTING -s ${LAB_CIDR} -o ${VPN_INTERFACE} -j RETURN 2>/dev/null || \\
        iptables -t nat -I POSTROUTING 1 -s ${LAB_CIDR} -o ${VPN_INTERFACE} -j RETURN; \\
    iptables -C FORWARD -i ${VPN_INTERFACE} -j DROP 2>/dev/null || \\
        iptables -A FORWARD -i ${VPN_INTERFACE} -j DROP'

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable ocr-vpn-firewall.service
    systemctl start ocr-vpn-firewall.service 2>/dev/null || true
    log "systemd ocr-vpn-firewall.service installed and enabled"
}

phase_6_firewall_ports() {
    header "Phase 6 — Firewall"

    info "Ensure these ports are open in your server's firewall:"
    echo "  - ${VPN_LISTEN_PORT}/udp   (WireGuard VPN)"
    echo "  - 80/tcp           (HTTP — platform frontend)"
    echo "  - 443/tcp          (HTTPS — if using SSL)"
    echo "  - 22/tcp           (SSH — for management)"
    echo ""

    # If ufw is active, add rules
    if command -v ufw &>/dev/null && ufw status | grep -q "active"; then
        ufw allow "${VPN_LISTEN_PORT}/udp" comment "WireGuard VPN" 2>/dev/null || true
        ufw allow 5000/tcp comment "Peer Manager API" 2>/dev/null || true
        ufw allow 80/tcp comment "HTTP" 2>/dev/null || true
        ufw allow 443/tcp comment "HTTPS" 2>/dev/null || true
        ufw allow 22/tcp comment "SSH" 2>/dev/null || true
        log "UFW rules added"
    else
        info "UFW not active — skipping"
    fi

    # Save iptables
    netfilter-persistent save 2>/dev/null || true
}

phase_7_platform() {
    header "Phase 7 — OpenCyberRange Platform"

    # Export deployment mode for install-platform.sh
    export OCR_VPN_ENABLED="true"
    export OCR_DEPLOYMENT_MODE="$DEPLOYMENT_MODE"
    # Ensure install-platform.sh uses the exact same runtime dir as this script.
    export OCR_PLATFORM_DIR="$PLATFORM_DIR"

    # WireGuard values (always populated — VPN is always installed)
    local server_pubkey=""
    server_pubkey=$(cat /etc/wireguard/server_public.key 2>/dev/null || echo "")

    if [ "$DEPLOYMENT_MODE" = "local" ]; then
        # ── Local mode: use LAN IP as VPN endpoint ───────────────────────
        local lan_ip=""
        lan_ip=$(ip -4 route get 1 2>/dev/null | awk '{print $7; exit}') || \
        lan_ip=$(hostname -I 2>/dev/null | awk '{print $1}') || \
        lan_ip=""

        if [ -n "$lan_ip" ]; then
            log "Detected local IP: ${lan_ip}"
        else
            lan_ip="localhost"
            warn "Could not detect local IP — using localhost"
        fi

        export OCR_WG_SERVER_PUBKEY="$server_pubkey"
        export OCR_WG_SERVER_ENDPOINT="${lan_ip}:${VPN_LISTEN_PORT}"
        export OCR_WG_API_KEY="$PEER_MANAGER_API_KEY"
        export OCR_WG_API_URL="http://host.docker.internal:${PEER_MANAGER_PORT}"
        export SERVER_PUBLIC_HOST="$lan_ip"
    else
        # ── Internet mode: use public IP as VPN endpoint ─────────────────
        local public_ip=""
        public_ip=$(curl -4 -s --connect-timeout 5 ifconfig.me 2>/dev/null || \
                    curl -4 -s --connect-timeout 5 icanhazip.com 2>/dev/null || \
                    curl -4 -s --connect-timeout 5 api.ipify.org 2>/dev/null || \
                    echo "")

        if [ -z "$public_ip" ]; then
            warn "Could not auto-detect this server's public IP address."
            echo -e "  ${YELLOW}This usually means the server has no internet access right now.${NC}"
            echo -e "  ${YELLOW}You can find it manually: curl -4 ifconfig.me${NC}"
            echo ""
            read -rp "  Enter this server's public IP address: " public_ip
            public_ip="${public_ip// /}"  # strip spaces
            if [ -z "$public_ip" ]; then
                warn "No IP provided — VPN endpoint will need to be set manually later."
                warn "Edit $PLATFORM_DIR/.env and set WG_SERVER_ENDPOINT=YOUR_IP:51820"
            fi
        fi

        export OCR_WG_SERVER_PUBKEY="$server_pubkey"
        export OCR_WG_SERVER_ENDPOINT="${public_ip:+${public_ip}:${VPN_LISTEN_PORT}}"
        export OCR_WG_API_KEY="$PEER_MANAGER_API_KEY"
        export OCR_WG_API_URL="http://host.docker.internal:${PEER_MANAGER_PORT}"
        export SERVER_PUBLIC_HOST="${public_ip:-localhost}"
    fi

    # A docker-compose.yml is written before images are built, so its presence
    # alone does not mean a good install: a Phase 7 build failure leaves the
    # compose behind, and skipping on that basis reports "Setup Complete" over a
    # half-install with an empty catalogue. Skip only when the platform is
    # actually up.
    platform_healthy() {
        [ -f "$PLATFORM_DIR/docker-compose.yml" ] || return 1
        ( cd "$PLATFORM_DIR" && docker compose ps backend 2>/dev/null | grep -qiE "up|running|healthy" )
    }
    if platform_healthy; then
        warn "Existing healthy platform found at $PLATFORM_DIR — skipping install. Use 'Update' to update."
    else
        if [ -f "$PLATFORM_DIR/docker-compose.yml" ]; then
            warn "A previous install is present but not running — repairing it."
        fi
        if [ -f "$REPO_DIR/scripts/install-platform.sh" ]; then
            info "Running platform installer..."
            echo ""
            # Run directly (not via sudo -u) so SUDO_USER from the outer
            # invocation is preserved.
            if bash "$REPO_DIR/scripts/install-platform.sh" --fresh; then
                chown -R "$REAL_USER":"$REAL_USER" "$PLATFORM_DIR" 2>/dev/null || true
                log "Platform installer finished"
            else
                chown -R "$REAL_USER":"$REAL_USER" "$PLATFORM_DIR" 2>/dev/null || true
                PLATFORM_INSTALL_FAILED=1
                err "Platform installation FAILED. The catalogue and services are not ready."
                err "Fix the error above and re-run: sudo bash scripts/setup-range-server.sh --install"
                return 1
            fi
        else
            die "install-platform.sh not found at $REPO_DIR/scripts/"
        fi
    fi
}

ensure_platform_running() {
    # Returns 0 if platform is running, 1 if not installed, 2 if user declined to start
    if [ ! -f "$PLATFORM_DIR/docker-compose.yml" ]; then
        err "Platform not installed yet."
        warn "Run ${BOLD}Install${NC} from the main menu first."
        return 1
    fi

    cd "$PLATFORM_DIR"
    if docker compose ps backend 2>/dev/null | grep -qi "up\|running"; then
        return 0
    fi

    warn "Platform containers are not running."
    read -rp "  Start them now? (Y/n): " start_choice
    if [[ "$start_choice" =~ ^[Nn]$ ]]; then
        return 2
    fi

    info "Starting platform containers..."
    if docker compose up -d; then
        # Wait for backend to be ready
        info "Waiting for backend to be ready..."
        local retries=0
        while [ $retries -lt 30 ]; do
            if docker compose ps backend 2>/dev/null | grep -qi "up\|running"; then
                sleep 2  # Give it a moment to finish startup
                log "Platform is running"
                return 0
            fi
            sleep 1
            retries=$((retries + 1))
        done
        warn "Backend may still be starting — continuing anyway."
        return 0
    else
        err "Failed to start platform containers."
        return 2
    fi
}

phase_7b_load_labs() {
    header "Load Labs"

    if ! ensure_platform_running; then
        return
    fi

    cd "$PLATFORM_DIR"

    # ── Step 1: Discover labs into the database ──────────────────────────────
    echo ""
    echo -e "  ${BOLD}Step 1 — Discover Labs${NC}"
    echo -e "  ${DIM}Scans the labs directory and registers them in the database.${NC}"
    echo -e "  ${DIM}This is fast (seconds).${NC}"
    echo ""
    read -rp "  Discover labs now? (Y/n): " discover_choice
    if [[ ! "$discover_choice" =~ ^[Nn]$ ]]; then
        info "Scanning labs directory..."
        local script_output=""
        local script_found=false

        if docker compose exec -T backend test -f /app/app/scripts/discover_labs.py 2>/dev/null; then
            script_output=$(docker compose exec -T backend python /app/app/scripts/discover_labs.py 2>&1)
            script_found=true
        elif docker compose exec -T backend test -f /app/scripts/discover_labs.py 2>/dev/null; then
            script_output=$(docker compose exec -T backend python /app/scripts/discover_labs.py 2>&1)
            script_found=true
        fi

        if [ "$script_found" = true ]; then
            echo "$script_output"
            log "${GREEN}✓ Lab discovery complete${NC}"
        else
            warn "discover_labs.py not found in container."
            warn "You can discover labs from the admin UI instead: Admin → Labs → Scan for Labs"
        fi
    else
        info "Skipped. You can discover labs later from the admin UI: Admin → Labs → Scan for Labs"
    fi

    # ── Step 2: Pre-build lab Docker images ──────────────────────────────────
    echo ""
    echo -e "  ${BOLD}Step 2 — Pre-build Lab Images${NC}"
    echo -e "  ${DIM}Builds Docker images for all labs so student spawns are instant.${NC}"
    echo -e "  ${YELLOW}  This can take a long time (10–60+ minutes depending on lab count).${NC}"
    echo ""
    read -rp "  Pre-build lab images now? (y/N): " prebuild_choice
    if [[ "$prebuild_choice" =~ ^[Yy]$ ]]; then
        local prebuild_script="$REPO_DIR/scripts/prebuild-labs.sh"
        if [ -f "$prebuild_script" ]; then
            chmod +x "$prebuild_script"
            info "Building lab images (this will take a while)..."
            if bash "$prebuild_script"; then
                log "${GREEN}✓ All lab images pre-built successfully${NC}"
            else
                warn "Some lab images failed to build — see output above."
                warn "Students may experience slower first spawns for those labs."
            fi
        else
            warn "prebuild-labs.sh not found at $prebuild_script"
        fi
    else
        info "Skipped. Labs will build on first student spawn (slower first launch)."
        info "You can pre-build later: bash $REPO_DIR/scripts/prebuild-labs.sh"
    fi
}

run_wstunnel() {
    if [ -f "$REPO_DIR/scripts/setup-wstunnel.sh" ]; then
        bash "$REPO_DIR/scripts/setup-wstunnel.sh"
    else
        die "setup-wstunnel.sh not found at $REPO_DIR/scripts/"
    fi
}

phase_7c_wstunnel() {
    header "WSTunnel (Optional)"

    echo ""
    echo -e "  ${BOLD}Do you need WSTunnel?${NC}"
    echo ""
    echo -e "  Answer ${BOLD}YES${NC} if:"
    echo -e "    • You are using ${BOLD}Cloudflare Tunnel${NC} (cloudflared) to expose this server"
    echo -e "    • Your server does NOT have a direct public IP, or"
    echo -e "    • Students will connect through Cloudflare instead of directly"
    echo ""
    echo -e "  Answer ${BOLD}NO${NC} if:"
    echo -e "    • Students connect directly to this server's IP address"
    echo -e "    • You are NOT using Cloudflare Tunnel"
    echo ""
    echo -e "  ${DIM}Not sure? Choose No — you can set this up later from the main menu.${NC}"
    echo ""
    read -rp "  Set up wstunnel? (y/N): " wstunnel_choice
    if [[ "$wstunnel_choice" =~ ^[Yy]$ ]]; then
        # Verify prerequisites before running
        if ! systemctl is-active --quiet cloudflared 2>/dev/null; then
            warn "cloudflared service is not running."
            echo -e "  ${YELLOW}WSTunnel requires Cloudflare Tunnel (cloudflared) to be set up first.${NC}"
            echo -e "  ${YELLOW}Set up cloudflared, then run WSTunnel from the main menu (option 4).${NC}"
            echo ""
            return
        fi
        run_wstunnel
    else
        info "Skipped. You can set up wstunnel later from the main menu (option 4)."
    fi
}

phase_7d_self_signed_cert() {
    header "Phase 7d — Self-Signed TLS Certificate"

    local CERT_DIR="$PLATFORM_DIR/certs"
    if [ -f "$CERT_DIR/selfsigned.crt" ]; then
        log "Self-signed certificate already exists at $CERT_DIR/"
        return
    fi

    local SERVER_IP
    SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
    if [ -z "$SERVER_IP" ]; then
        warn "Could not detect server IP — skipping cert generation"
        info "Generate manually later: sudo bash scripts/generate-self-signed-cert.sh <IP>"
        return
    fi

    OCR_CERT_DIR="$PLATFORM_DIR/certs" bash "$REPO_DIR/scripts/generate-self-signed-cert.sh" "$SERVER_IP"
    if [ ! -f "$PLATFORM_DIR/certs/selfsigned.crt" ]; then
        warn "Certificate was not written to $PLATFORM_DIR/certs — HTTPS not enabled. Platform works on HTTP."
        return
    fi

    # Rebuild frontend to pick up the entrypoint, then restart
    info "Rebuilding frontend container with HTTPS support..."
    (cd "$PLATFORM_DIR" && docker compose up -d --force-recreate frontend) || {
        warn "Frontend restart failed — HTTPS not active. Platform still works on HTTP."
        return
    }
    sleep 3
    if curl -ksS -o /dev/null "https://127.0.0.1/" 2>/dev/null; then
        log "HTTPS enabled on port 443 (self-signed certificate for $SERVER_IP)"
    else
        warn "HTTPS did not come up on 443 (cert present but not serving). Platform works on HTTP; check 'docker compose logs frontend'."
    fi
}

phase_8_verification() {
    header "Phase 8 — Verification"

    echo ""
    PASS=0
    FAIL=0

    check() {
        if eval "$2" &>/dev/null; then
            log "$1"
            PASS=$((PASS + 1))
        else
            err "$1"
            FAIL=$((FAIL + 1))
        fi
    }

    # ── Core checks (always) ──
    check "Docker running"                       "systemctl is-active docker"
    check "Docker Compose available"             "docker compose version"
    check "IP forwarding enabled"                "[ \$(cat /proc/sys/net/ipv4/ip_forward) = 1 ]"

    # ── VPN checks (only if WireGuard is installed) ──
    local vpn_installed=false
    if [ -f "/etc/wireguard/${VPN_INTERFACE}.conf" ]; then
        vpn_installed=true
    fi

    if [ "$vpn_installed" = true ]; then
        check "WireGuard config exists"              "[ -f /etc/wireguard/${VPN_INTERFACE}.conf ]"
        check "WireGuard service running"            "systemctl is-active wg-quick@${VPN_INTERFACE}"
        check "WireGuard listening on ${VPN_LISTEN_PORT}" "ss -ulnp | grep -q :${VPN_LISTEN_PORT}"
        check "Peer Manager service running"         "systemctl is-active ocr-peer-manager"
        check "Peer Manager API responds"            "curl -sf http://127.0.0.1:${PEER_MANAGER_PORT}/health"
        check "Server keys exist"                    "[ -f /etc/wireguard/server_public.key ]"
        check "VPN firewall service enabled"         "systemctl is-enabled ocr-vpn-firewall"
        check "iptables raw PREROUTING rule"         "iptables -t raw -C PREROUTING -i ${VPN_INTERFACE} -d ${LAB_CIDR} -j ACCEPT"
        check "iptables FORWARD inbound rule"        "iptables -C FORWARD -i ${VPN_INTERFACE} -d ${LAB_CIDR} -j ACCEPT"
        check "iptables FORWARD outbound rule"       "iptables -C FORWARD -o ${VPN_INTERFACE} -s ${LAB_CIDR} -j ACCEPT"
        check "iptables NAT skip-MASQUERADE rule"    "iptables -t nat -C POSTROUTING -s ${LAB_CIDR} -o ${VPN_INTERFACE} -j RETURN"
        check "iptables VPN non-lab DROP rule"      "iptables -C FORWARD -i ${VPN_INTERFACE} -j DROP"
    else
        info "VPN not installed — skipping WireGuard checks"
    fi

    # ── Platform checks ──
    if [ -f "$PLATFORM_DIR/docker-compose.yml" ]; then
        check "Platform docker-compose.yml exists" "true"
        check "Backend container running"  "docker compose -f '$PLATFORM_DIR/docker-compose.yml' ps backend 2>/dev/null | grep -qi 'up\|running'"
        check "Frontend container running" "docker compose -f '$PLATFORM_DIR/docker-compose.yml' ps frontend 2>/dev/null | grep -qi 'up\|running'"
        check "Database container running" "docker compose -f '$PLATFORM_DIR/docker-compose.yml' ps db 2>/dev/null | grep -qi 'up\|running'"

        # Timezone consistency
        check "PostgreSQL timezone is UTC" \
            "docker compose -f '$PLATFORM_DIR/docker-compose.yml' exec -T db psql -U labuser -d labdb -tAc 'SHOW timezone;' 2>/dev/null | grep -qi 'utc'"
        check "Backend timezone is UTC" \
            "docker compose -f '$PLATFORM_DIR/docker-compose.yml' exec -T backend python3 -c 'import time; assert time.timezone == 0' 2>/dev/null"

        # Backend health
        check "Backend API health endpoint" \
            "curl -sf http://127.0.0.1:8000/health"

        # RangeBox images
        check "RangeBox image built" \
            "docker images -q opencyberrange/rangebox:lite 2>/dev/null | grep -q ."
    fi

    # ── Environment variable checks ──
    if [ -f "$PLATFORM_DIR/.env" ]; then
        check ".env has JWT_SECRET"           "grep -q '^JWT_SECRET=' '$PLATFORM_DIR/.env'"
        check ".env has DATABASE_URL"         "grep -q '^DATABASE_URL=' '$PLATFORM_DIR/.env'"

        # VPN-specific env vars (only if VPN is installed)
        if [ "$vpn_installed" = true ]; then
            check ".env has WG_SERVER_ENDPOINT"   "grep -q '^WG_SERVER_ENDPOINT=' '$PLATFORM_DIR/.env'"
            check ".env has WG_SERVER_PUBLIC_KEY" "grep -q '^WG_SERVER_PUBLIC_KEY=' '$PLATFORM_DIR/.env'"
            check ".env has WG_API_KEY"           "grep -q '^WG_API_KEY=' '$PLATFORM_DIR/.env'"
            check ".env has WG_ENCRYPTION_KEY"    "grep -q '^WG_ENCRYPTION_KEY=' '$PLATFORM_DIR/.env'"
        fi
    fi

    # ── WSTunnel (optional — only check if service exists) ──
    if systemctl list-unit-files 2>/dev/null | grep -q 'ocr-wstunnel'; then
        check "WSTunnel service running"   "systemctl is-active ocr-wstunnel"
        check "WSTunnel listening on 8443" "ss -tlnp | grep -q ':8443'"
    fi

    # ── HTTPS (optional — only check if certs exist) ──
    if [ -f "$PLATFORM_DIR/certs/selfsigned.crt" ]; then
        check "Self-signed TLS certificate present" "[ -f '$PLATFORM_DIR/certs/selfsigned.crt' ]"
        check "HTTPS port 443 responding"           "curl -sfk https://127.0.0.1/ -o /dev/null"
    fi

    echo ""
    echo -e "${CYAN}─────────────────────────────────────────${NC}"
    echo -e "  Results: ${GREEN}${PASS} passed${NC}, ${RED}${FAIL} failed${NC}"
    echo -e "${CYAN}─────────────────────────────────────────${NC}"
    echo ""

    if [ "$FAIL" -gt 0 ]; then
        warn "Some checks failed. Review the output above."
    fi
}

show_summary() {
    echo ""
    echo -e "${GREEN}${BOLD}     ██████╗  ██████╗██████╗ ${NC}"
    echo -e "${GREEN}${BOLD}    ██╔═══██╗██╔════╝██╔══██╗${NC}"
    echo -e "${GREEN}${BOLD}    ██║   ██║██║     ██████╔╝${NC}"
    echo -e "${GREEN}${BOLD}    ██║   ██║██║     ██╔══██╗${NC}"
    echo -e "${GREEN}${BOLD}    ╚██████╔╝╚██████╗██║  ██║${NC}"
    echo -e "${GREEN}${BOLD}     ╚═════╝  ╚═════╝╚═╝  ╚═╝${NC}"
    echo ""
    echo -e "${BOLD}${GREEN}    ╔═══════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${GREEN}    ║${NC}${BOLD}   Setup Complete                       ${GREEN}${BOLD}║${NC}"
    echo -e "${BOLD}${GREEN}    ╚═══════════════════════════════════════╝${NC}"
    echo ""

    SERVER_PUBKEY=$(cat /etc/wireguard/server_public.key 2>/dev/null || echo "<not generated yet>")
    echo -e "  ${DIM}──────────────────────────────────────────${NC}"
    if [ "$DEPLOYMENT_MODE" = "local" ]; then
        echo -e "  ${BOLD}Mode${NC}               : ${CYAN}Local network (VPN + self-signed HTTPS)${NC}"
    else
        echo -e "  ${BOLD}Mode${NC}               : ${CYAN}Internet / Cloud (VPN + public endpoint)${NC}"
    fi
    echo -e "  ${BOLD}Server Public Key${NC}  : ${CYAN}${SERVER_PUBKEY}${NC}"
    echo -e "  ${BOLD}Peer Manager Key${NC}   : ${DIM}(stored in ${PEER_MANAGER_DIR}/peer_manager.env)${NC}"
    echo -e "  ${BOLD}Peer Manager URL${NC}   : ${CYAN}http://${PEER_MANAGER_BIND}:${PEER_MANAGER_PORT}${NC}"
    echo -e "  ${DIM}──────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}${MAGENTA}Next steps:${NC}"
    echo -e "    ${CYAN}1.${NC} Verify VPN: ${DIM}sudo wg show${NC}"
    echo -e "    ${CYAN}2.${NC} Access platform: ${BOLD}https://localhost${NC}"
    echo -e "    ${CYAN}3.${NC} Share the server's IP with students"
    echo ""
    echo -e "  ${DIM}WireGuard config : /etc/wireguard/${VPN_INTERFACE}.conf${NC}"
    echo -e "  ${DIM}Firewall service : ocr-vpn-firewall.service${NC}"

    echo -e "  ${DIM}Platform dir     : $PLATFORM_DIR${NC}"
    echo ""
}

# ==============================================================================
# INTERACTIVE MENUS
# ==============================================================================

show_main_menu() {
    # Show quick platform status indicator
    local platform_status=""
    if [ -f "$PLATFORM_DIR/docker-compose.yml" ]; then
        if docker compose -f "$PLATFORM_DIR/docker-compose.yml" ps backend 2>/dev/null | grep -qi "up\|running"; then
            platform_status="${GREEN}● running${NC}"
        else
            platform_status="${RED}● stopped${NC}"
        fi
    else
        platform_status="${YELLOW}● not installed${NC}"
    fi
    echo -e "  ${DIM}Platform: ${platform_status}${NC}"
    echo ""

    echo -e "  ${BOLD}What would you like to do?${NC}"
    echo ""
    echo -e "    ${CYAN}1)${NC} ${BOLD}Install${NC}    — Full server setup (all phases)"
    echo -e "    ${CYAN}2)${NC} ${BOLD}Update${NC}     — Update platform (pull changes, rebuild)"
    echo -e "    ${CYAN}3)${NC} ${BOLD}Load Labs${NC}  — Discover labs & pre-build images"
    echo -e "    ${CYAN}4)${NC} ${BOLD}WSTunnel${NC}   — Set up VPN over Cloudflare Tunnel"
    echo -e "    ${CYAN}5)${NC} ${BOLD}Platform${NC}   — Start / stop / restart containers"
    echo -e "    ${CYAN}6)${NC} ${BOLD}Fix${NC}        — Repair/restart specific components"
    echo -e "    ${CYAN}7)${NC} ${BOLD}Status${NC}     — Check system health"
    echo -e "    ${CYAN}8)${NC} ${BOLD}Exit${NC}"
    echo ""
    read -rp "  Select [1-8]: " choice || choice="8"
    case "$choice" in
        1) ACTION="install" ;;
        2) ACTION="update" ;;
        3) ACTION="load_labs" ;;
        4) ACTION="wstunnel" ;;
        5) ACTION="platform" ;;
        6) ACTION="fix" ;;
        7) ACTION="status" ;;
        8) echo ""; log "Goodbye!"; exit 0 ;;
        *)
            warn "Invalid choice — enter 1–8"
            echo ""
            show_main_menu
            ;;
    esac
}

run_fix_menu() {
    echo ""
    echo -e "  ${BOLD}What would you like to fix?${NC}"
    echo ""
    echo -e "    ${CYAN}1)${NC} Packages       — Reinstall system packages"
    echo -e "    ${CYAN}2)${NC} WireGuard      — Restart WireGuard VPN"
    echo -e "    ${CYAN}3)${NC} Peer Manager   — Recreate venv, reinstall Flask, restart"
    echo -e "    ${CYAN}4)${NC} Firewall       — Re-apply VPN iptables rules"
    echo -e "    ${CYAN}5)${NC} Platform       — Re-run platform installer"
    echo -e "    ${CYAN}6)${NC} All            — Run all fixes"
    echo -e "    ${CYAN}7)${NC} Back           — Return to main menu"
    echo ""
    read -rp "  Select [1-7]: " fix_choice || fix_choice=""
    case "$fix_choice" in
        1) phase_1_packages ;;
        2) phase_2_ip_forwarding; phase_3_wireguard ;;
        3) phase_4_peer_manager ;;
        4) phase_5_firewall_rules; phase_6_firewall_ports ;;
        5) phase_7_platform ;;
        6)
            phase_1_packages
            phase_2_ip_forwarding
            phase_3_wireguard
            phase_4_peer_manager
            phase_5_firewall_rules
            phase_6_firewall_ports
            phase_7_platform
            ;;
        7) return ;;
        *)
            warn "Invalid choice — returning to main menu"
            return
            ;;
    esac
    phase_8_verification
}

# ==============================================================================
# MAIN DISPATCH
# ==============================================================================

run_platform_menu() {
    if [ ! -f "$PLATFORM_DIR/docker-compose.yml" ]; then
        err "Platform not installed yet."
        warn "Run ${BOLD}Install${NC} from the main menu first."
        return
    fi

    cd "$PLATFORM_DIR"

    # Show current container status
    echo ""
    echo -e "  ${BOLD}Container Status:${NC}"
    echo ""
    docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || \
        docker compose ps 2>/dev/null || \
        warn "Could not retrieve container status"
    echo ""

    echo -e "  ${BOLD}Platform Actions:${NC}"
    echo ""
    echo -e "    ${CYAN}1)${NC} ${BOLD}Start${NC}      — Start all containers"
    echo -e "    ${CYAN}2)${NC} ${BOLD}Stop${NC}       — Stop all containers"
    echo -e "    ${CYAN}3)${NC} ${BOLD}Restart${NC}    — Restart all containers"
    echo -e "    ${CYAN}4)${NC} ${BOLD}Logs${NC}       — Show recent backend logs"
    echo -e "    ${CYAN}5)${NC} ${BOLD}Back${NC}       — Return to main menu"
    echo ""
    read -rp "  Select [1-5]: " platform_choice || platform_choice=""
    case "$platform_choice" in
        1)
            info "Starting platform containers..."
            docker compose up -d && log "Platform started" || err "Failed to start platform"
            ;;
        2)
            info "Stopping platform containers..."
            docker compose down && log "Platform stopped" || err "Failed to stop platform"
            ;;
        3)
            info "Restarting platform containers..."
            docker compose down && docker compose up -d && log "Platform restarted" || err "Failed to restart platform"
            ;;
        4)
            info "Recent backend logs (last 50 lines):"
            echo ""
            docker compose logs --tail=50 backend 2>&1
            ;;
        5) return ;;
        *)
            warn "Invalid choice — returning to main menu"
            return
            ;;
    esac
}

run_update() {
    header "Update — Platform"

    if [ ! -f "$PLATFORM_DIR/docker-compose.yml" ]; then
        err "No existing installation found at $PLATFORM_DIR"
        warn "Run Install first to set up the platform."
        return
    fi

    if [ -f "$REPO_DIR/scripts/deploy-updates.sh" ]; then
        info "Running platform update..."
        bash "$REPO_DIR/scripts/deploy-updates.sh" --all
        log "Platform update finished"
    else
        die "deploy-updates.sh not found at $REPO_DIR/scripts/"
    fi
}

run_action() {
    case "$ACTION" in
        install)
            phase_1_packages
            phase_2_ip_forwarding
            prompt_deployment_scenario
            phase_3_wireguard
            phase_4_peer_manager
            phase_5_firewall_rules
            phase_6_firewall_ports
            phase_7_platform
            phase_7b_load_labs
            if [ "$DEPLOYMENT_MODE" = "internet" ]; then
                phase_7c_wstunnel
            fi
            if [ "${GENERATE_SELF_SIGNED:-false}" = true ]; then
                phase_7d_self_signed_cert
            fi
            phase_8_verification
            restore_clone_ownership
            show_summary
            ;;
        update)
            run_update
            ;;
        load_labs)
            phase_7b_load_labs
            ;;
        wstunnel)
            run_wstunnel
            ;;
        platform)
            run_platform_menu
            ;;
        fix)
            run_fix_menu
            ;;
        status)
            phase_8_verification
            ;;
        *)
            die "Unknown action: $ACTION"
            ;;
    esac
}

# If a CLI flag was provided, run once and exit
if [ -n "$ACTION" ]; then
    run_action
else
    # Interactive mode — loop back to the menu after each action
    while true; do
        ACTION=""
        show_main_menu
        run_action
        echo ""
        read -rp "  Press Enter to return to the menu..." _
        echo ""
    done
fi
