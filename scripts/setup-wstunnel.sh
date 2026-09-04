#!/bin/bash
# ==============================================================================
# OpenCyberRange — WSTunnel Setup for VPN over Cloudflare Tunnel
# ==============================================================================
#
# This script sets up wstunnel to wrap WireGuard UDP traffic inside WebSocket
# connections, allowing it to traverse Cloudflare Tunnel (which only supports TCP).
#
# Architecture:
#   Student WireGuard -> wstunnel client (UDP->WebSocket) -> Cloudflare Tunnel
#   -> wstunnel server (WebSocket->UDP) -> WireGuard server (localhost:51820)
#
# USAGE:
#   sudo bash setup-wstunnel.sh
#
# PREREQUISITES:
#   - WireGuard already running on UDP 51820
#   - Cloudflare Tunnel (cloudflared) already configured and running
#   - A DNS record or hostname available for VPN traffic (e.g. vpn.yourdomain.com)
#
# ==============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Configuration
WSTUNNEL_VERSION="10.5.2"
WSTUNNEL_PORT=8443
WSTUNNEL_BIND="127.0.0.1"
WIREGUARD_PORT=51820
INSTALL_DIR="/usr/local/bin"
SERVICE_NAME="ocr-wstunnel"

log() { echo -e "$1"; }
error_exit() { log "${RED}ERROR: $1${NC}"; exit 1; }

# ── Pre-flight checks ─────────────────────────────────────────────────────────

log "${CYAN}=== OpenCyberRange WSTunnel Setup ===${NC}"
log ""

# Must run as root
if [ "$EUID" -ne 0 ]; then
    error_exit "This script must be run with sudo: sudo bash $0"
fi

# Check WireGuard is running
if ! ss -ulnp | grep -q ":${WIREGUARD_PORT}"; then
    error_exit "WireGuard is not listening on UDP port ${WIREGUARD_PORT}. Start WireGuard first."
fi
log "${GREEN}✓ WireGuard running on UDP ${WIREGUARD_PORT}${NC}"

# Check cloudflared is running
if ! systemctl is-active --quiet cloudflared; then
    error_exit "cloudflared service is not running. Start it first."
fi
log "${GREEN}✓ cloudflared service is active${NC}"

# Check cloudflared config exists
CLOUDFLARED_CONFIG="/etc/cloudflared/config.yml"
if [ ! -f "$CLOUDFLARED_CONFIG" ]; then
    error_exit "Cloudflare tunnel config not found at $CLOUDFLARED_CONFIG"
fi
log "${GREEN}✓ cloudflared config found${NC}"

# ── Step 1: Install wstunnel binary ───────────────────────────────────────────

log ""
log "${BLUE}Step 1: Installing wstunnel v${WSTUNNEL_VERSION}...${NC}"

ARCH=$(uname -m)
case "$ARCH" in
    x86_64)  ARCH_SUFFIX="amd64" ;;
    aarch64) ARCH_SUFFIX="arm64" ;;
    *)       error_exit "Unsupported architecture: $ARCH" ;;
esac

# Check if already installed at correct version
if command -v wstunnel &> /dev/null; then
    CURRENT_VERSION=$(wstunnel --version 2>&1 | grep -oP '[\d.]+' || echo "unknown")
    if [ "$CURRENT_VERSION" = "$WSTUNNEL_VERSION" ]; then
        log "${GREEN}✓ wstunnel v${WSTUNNEL_VERSION} already installed${NC}"
    else
        log "${YELLOW}Upgrading wstunnel from v${CURRENT_VERSION} to v${WSTUNNEL_VERSION}${NC}"
    fi
fi

# Download if not the right version
if ! command -v wstunnel &> /dev/null || [ "$CURRENT_VERSION" != "$WSTUNNEL_VERSION" ]; then
    DOWNLOAD_URL="https://github.com/erebe/wstunnel/releases/download/v${WSTUNNEL_VERSION}/wstunnel_${WSTUNNEL_VERSION}_linux_${ARCH_SUFFIX}.tar.gz"
    TMP_DIR=$(mktemp -d)

    log "Downloading from ${DOWNLOAD_URL}..."
    if ! curl -sL "$DOWNLOAD_URL" -o "$TMP_DIR/wstunnel.tar.gz"; then
        # Try using pre-downloaded copy
        if [ -f "/tmp/wstunnel" ]; then
            log "${YELLOW}Download failed, using pre-downloaded binary${NC}"
            cp /tmp/wstunnel "$INSTALL_DIR/wstunnel"
        else
            error_exit "Failed to download wstunnel"
        fi
    else
        tar -xzf "$TMP_DIR/wstunnel.tar.gz" -C "$TMP_DIR/"
        cp "$TMP_DIR/wstunnel" "$INSTALL_DIR/wstunnel"
    fi

    chmod +x "$INSTALL_DIR/wstunnel"
    rm -rf "$TMP_DIR"

    log "${GREEN}✓ wstunnel installed to ${INSTALL_DIR}/wstunnel${NC}"
fi

# Verify
"$INSTALL_DIR/wstunnel" --version

# ── Step 2: Create systemd service ────────────────────────────────────────────

log ""
log "${BLUE}Step 2: Creating systemd service...${NC}"

cat > "/etc/systemd/system/${SERVICE_NAME}.service" << EOF
[Unit]
Description=OpenCyberRange WSTunnel - WebSocket to WireGuard UDP relay
Documentation=https://github.com/erebe/wstunnel
After=network.target
After=wg-quick@wg0.service
Wants=network-online.target

[Service]
Type=simple
ExecStart=${INSTALL_DIR}/wstunnel server \\
    --restrict-to 127.0.0.1:${WIREGUARD_PORT} \\
    ws://${WSTUNNEL_BIND}:${WSTUNNEL_PORT}
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=ocr-wstunnel

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

log "${GREEN}✓ Service file created: /etc/systemd/system/${SERVICE_NAME}.service${NC}"

# ── Step 3: Update Cloudflare tunnel config ───────────────────────────────────

log ""
log "${BLUE}Step 3: Updating Cloudflare tunnel config...${NC}"

# Detect the hostname from existing config
EXISTING_HOSTNAME=$(grep -oP 'hostname:\s*\K\S+' "$CLOUDFLARED_CONFIG" | head -1)
if [ -z "$EXISTING_HOSTNAME" ]; then
    error_exit "Could not detect hostname from cloudflared config"
fi

# Derive the VPN hostname from the existing hostname
# e.g., labs.attackanddefend.com -> vpn.attackanddefend.com
DOMAIN=$(echo "$EXISTING_HOSTNAME" | sed 's/^[^.]*\.//')
VPN_HOSTNAME="vpn.${DOMAIN}"

log "Detected domain: ${DOMAIN}"
log "VPN hostname will be: ${VPN_HOSTNAME}"

# Check if VPN ingress already exists
if grep -q "$VPN_HOSTNAME" "$CLOUDFLARED_CONFIG"; then
    log "${YELLOW}⚠ VPN hostname already in cloudflared config — skipping${NC}"
else
    # Backup config
    cp "$CLOUDFLARED_CONFIG" "${CLOUDFLARED_CONFIG}.bak.$(date +%Y%m%d_%H%M%S)"
    log "✓ Config backed up"

    # Insert the VPN ingress rule BEFORE the catch-all rule
    # The catch-all rule (- service: http_status:404) must remain last
    python3 << PYEOF
import yaml, sys, shutil

config_path = "${CLOUDFLARED_CONFIG}"

with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

if 'ingress' not in config:
    print("ERROR: No ingress rules found in config")
    sys.exit(1)

# Check if VPN rule already exists
for rule in config['ingress']:
    if rule.get('hostname') == "${VPN_HOSTNAME}":
        print("VPN rule already exists, skipping")
        sys.exit(0)

# Insert VPN rule before the catch-all (last rule)
vpn_rule = {
    'hostname': '${VPN_HOSTNAME}',
    'service': 'ws://${WSTUNNEL_BIND}:${WSTUNNEL_PORT}'
}

# Insert before the last rule (catch-all)
config['ingress'].insert(-1, vpn_rule)

with open(config_path, 'w') as f:
    yaml.dump(config, f, default_flow_style=False, sort_keys=False)

print("VPN ingress rule added successfully")
PYEOF

    log "${GREEN}✓ Cloudflare tunnel config updated${NC}"
fi

# ── Step 4: Enable and start services ─────────────────────────────────────────

log ""
log "${BLUE}Step 4: Starting services...${NC}"

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"
systemctl start "${SERVICE_NAME}"

# Verify wstunnel is running
sleep 2
if systemctl is-active --quiet "${SERVICE_NAME}"; then
    log "${GREEN}✓ ${SERVICE_NAME} service is running${NC}"
else
    log "${RED}✗ ${SERVICE_NAME} failed to start. Check: journalctl -u ${SERVICE_NAME}${NC}"
    exit 1
fi

# Restart cloudflared to pick up new config
log "Restarting cloudflared to apply new ingress rule..."
systemctl restart cloudflared

sleep 3
if systemctl is-active --quiet cloudflared; then
    log "${GREEN}✓ cloudflared restarted successfully${NC}"
else
    log "${RED}✗ cloudflared failed to restart. Check: journalctl -u cloudflared${NC}"
    log "${YELLOW}Restoring backup config...${NC}"
    LATEST_BACKUP=$(ls -t ${CLOUDFLARED_CONFIG}.bak.* 2>/dev/null | head -1)
    if [ -n "$LATEST_BACKUP" ]; then
        cp "$LATEST_BACKUP" "$CLOUDFLARED_CONFIG"
        systemctl restart cloudflared
    fi
    exit 1
fi

# ── Step 5: Verify ────────────────────────────────────────────────────────────

log ""
log "${BLUE}Step 5: Verifying setup...${NC}"

# Check wstunnel is listening
if ss -tlnp | grep -q ":${WSTUNNEL_PORT}"; then
    log "${GREEN}✓ wstunnel listening on ${WSTUNNEL_BIND}:${WSTUNNEL_PORT}${NC}"
else
    log "${RED}✗ wstunnel is NOT listening on port ${WSTUNNEL_PORT}${NC}"
fi

# Check WireGuard is still running
if ss -ulnp | grep -q ":${WIREGUARD_PORT}"; then
    log "${GREEN}✓ WireGuard listening on UDP ${WIREGUARD_PORT}${NC}"
else
    log "${RED}✗ WireGuard is NOT listening${NC}"
fi

# Check cloudflared
if systemctl is-active --quiet cloudflared; then
    log "${GREEN}✓ cloudflared is running${NC}"
else
    log "${RED}✗ cloudflared is NOT running${NC}"
fi

# ── Summary ───────────────────────────────────────────────────────────────────

log ""
log "${GREEN}========================================${NC}"
log "${GREEN}WSTunnel setup complete!${NC}"
log "${GREEN}========================================${NC}"
log ""
log "${BOLD}Architecture:${NC}"
log "  Student WireGuard"
log "    -> wstunnel client (local, UDP -> WebSocket)"
log "    -> Cloudflare Tunnel (${VPN_HOSTNAME})"
log "    -> wstunnel server (${WSTUNNEL_BIND}:${WSTUNNEL_PORT}, WebSocket -> UDP)"
log "    -> WireGuard (localhost:${WIREGUARD_PORT})"
log ""
log "${BOLD}Services:${NC}"
log "  wstunnel:    systemctl {start|stop|status} ${SERVICE_NAME}"
log "  cloudflared: systemctl {start|stop|status} cloudflared"
log "  wireguard:   systemctl {start|stop|status} wg-quick@wg0"
log ""
log "${CYAN}${BOLD}IMPORTANT — Cloudflare Dashboard Setup Required:${NC}"
log ""
log "  You MUST create a DNS record in Cloudflare for: ${BOLD}${VPN_HOSTNAME}${NC}"
log ""
log "  Go to: Cloudflare Dashboard -> ${DOMAIN} -> DNS -> Add Record"
log "    Type:    CNAME"
log "    Name:    vpn"
log "    Target:  ${EXISTING_HOSTNAME}"
log "    Proxy:   ON (orange cloud)"
log ""
log "  Then go to: Network settings for ${DOMAIN}"
log "    Ensure 'WebSockets' is enabled (usually on by default)"
log ""
log "${BOLD}Student Setup:${NC}"
log "  Students must run wstunnel client on their machine."
log "  See the documentation for full student instructions."
log ""
