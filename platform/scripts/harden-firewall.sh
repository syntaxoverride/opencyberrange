#!/usr/bin/env bash
# ============================================================================
# OpenCyberRange — Firewall Hardening Script
# ============================================================================
#
# PURPOSE
#   Adds iptables DOCKER-USER rules that prevent any external (non-Docker)
#   network interface from forwarding traffic into Docker-internal lab
#   networks. This ensures the QEMU-based Windows target, student lab
#   containers, RangeBoxes, and SIEM containers are unreachable from the
#   physical LAN, the internet, or any other non-platform network.
#
# HOW IT WORKS
#   1. Auto-detects all "external" interfaces — physical NICs, VPNs, tunnels,
#      and anything that is NOT a Docker-managed interface (docker0, br-*,
#      veth*) or loopback.
#   2. For each external interface × protected subnet, inserts a DROP rule
#      at the top of the DOCKER-USER chain (if not already present).
#   3. Saves the rules to /etc/iptables/rules.v4 for persistence.
#
#   Published ports (e.g. port 80 for the frontend) are NOT affected. Docker
#   handles published ports via PREROUTING DNAT — the destination IP is
#   rewritten to the container's bridge address BEFORE the FORWARD chain is
#   evaluated, so these rules (which match only OCR-internal subnets) do not
#   interfere.
#
# EXTERNAL INTERFACE DETECTION
#   By default, the script detects the interface carrying the default route
#   (the one facing the physical LAN / internet). This is the primary
#   interface to block. VPN / tunnel interfaces (wg0, tailscale0) are
#   intentional admin/student access paths and are NOT blocked by default.
#
#   Override: set OCR_EXTERNAL_IFACES="eth0 wlan0" to skip auto-detection.
#   Aggressive: set OCR_BLOCK_ALL_EXTERNAL=1 to block ALL non-Docker
#               interfaces (then use OCR_ALLOWED_IFACES to exempt VPNs).
#
# PROTECTED SUBNETS
#   By default the script protects these OCR-internal ranges:
#     10.150.0.0/24  — Windows target / shared container native networks
#     10.100.0.0/16  — Student lab networks
#     10.50.0.0/16   — RangeBox standalone networks
#     10.200.0.0/16  — SIEM / SOC networks
#
#   Override: set OCR_PROTECTED_NETS="10.150.0.0/24 10.100.0.0/16" etc.
#
# WHEN TO RUN
#   - After a fresh install or host reboot (if netfilter-persistent fails)
#   - After Docker recreates the DOCKER-USER chain (rare; only on daemon restart)
#   - The script is idempotent — safe to re-run without creating duplicate rules
#
# REQUIRES
#   - Root privileges (or run via privileged Docker container — see below)
#   - iptables (nf_tables backend)
#
# USAGE
#   Option 1 (with sudo):
#     sudo bash /path/to/harden-firewall.sh
#
#   Option 2 (without sudo, via privileged Docker container):
#     docker run --rm --net=host --privileged \
#       -v /path/to/harden-firewall.sh:/run.sh:ro \
#       -v /etc/iptables:/etc/iptables \
#       alpine sh -c "apk add -q iptables bash && bash /run.sh"
# ============================================================================

set -euo pipefail

# --- Configuration (overridable via environment) ----------------------------

# Protected subnets — traffic from external interfaces to these is DROPped
OCR_PROTECTED_NETS="${OCR_PROTECTED_NETS:-10.150.0.0/24 10.100.0.0/16 10.50.0.0/16 10.200.0.0/16}"

# Interfaces to explicitly allow (exempt from blocking in block-all mode)
OCR_ALLOWED_IFACES="${OCR_ALLOWED_IFACES:-}"

# External interfaces (auto-detected if not set)
OCR_EXTERNAL_IFACES="${OCR_EXTERNAL_IFACES:-}"

# Set to "1" to block ALL non-Docker interfaces instead of just the default route
OCR_BLOCK_ALL_EXTERNAL="${OCR_BLOCK_ALL_EXTERNAL:-0}"

# --- Functions ---------------------------------------------------------------

detect_default_route_iface() {
    # Returns just the interface carrying the default route
    ip -4 route show default 2>/dev/null | awk '{print $5; exit}'
}

detect_all_external_ifaces() {
    # List all UP interfaces, then exclude Docker-managed ones and loopback.
    # What remains are physical NICs, VPNs, tunnels — anything "external".
    local all_ifaces
    all_ifaces=$(ip -o link show up 2>/dev/null | awk -F': ' '{print $2}' | sed 's/@.*//')

    local external=""
    for iface in $all_ifaces; do
        case "$iface" in
            lo|docker0|docker[0-9]*) continue ;;  # loopback, Docker default bridge
            br-*)                    continue ;;  # Docker custom network bridges
            veth*)                   continue ;;  # Docker container veth pairs
        esac
        external="$external $iface"
    done
    echo "$external" | xargs  # trim whitespace
}

is_allowed() {
    local iface="$1"
    for allowed in $OCR_ALLOWED_IFACES; do
        [ "$iface" = "$allowed" ] && return 0
    done
    return 1
}

rule_exists() {
    local iface="$1" net="$2"
    iptables -C DOCKER-USER -i "$iface" -d "$net" -j DROP 2>/dev/null
}

add_rule() {
    local iface="$1" net="$2" label="$3"
    if rule_exists "$iface" "$net"; then
        echo "  [SKIP] $iface → $net ($label) — already exists"
    else
        iptables -I DOCKER-USER 1 -i "$iface" -d "$net" -j DROP \
            -m comment --comment "OCR: block $iface->$label"
        echo "  [ADD]  $iface → $net ($label)"
    fi
}

# Human-readable label for a subnet
subnet_label() {
    case "$1" in
        10.150.0.0/24) echo "shared-containers" ;;
        10.100.0.0/16) echo "lab-networks" ;;
        10.50.0.0/16)  echo "rangebox-networks" ;;
        10.200.0.0/16) echo "siem-networks" ;;
        *)             echo "protected-net" ;;
    esac
}

# --- Main --------------------------------------------------------------------

echo "=== OpenCyberRange Firewall Hardening ==="
echo ""

# Detect or use provided external interfaces
if [ -n "$OCR_EXTERNAL_IFACES" ]; then
    EXT_IFACES="$OCR_EXTERNAL_IFACES"
    echo "External interfaces (from OCR_EXTERNAL_IFACES): $EXT_IFACES"
elif [ "$OCR_BLOCK_ALL_EXTERNAL" = "1" ]; then
    EXT_IFACES=$(detect_all_external_ifaces)
    echo "External interfaces (auto-detected, block-all mode): $EXT_IFACES"
else
    EXT_IFACES=$(detect_default_route_iface)
    echo "Default-route interface (auto-detected): $EXT_IFACES"
fi

if [ -z "$EXT_IFACES" ]; then
    echo "WARNING: No external interfaces detected. Nothing to do."
    exit 0
fi

# Filter out allowed interfaces
BLOCKED_IFACES=""
for iface in $EXT_IFACES; do
    if is_allowed "$iface"; then
        echo "  [EXEMPT] $iface (in OCR_ALLOWED_IFACES)"
    else
        BLOCKED_IFACES="$BLOCKED_IFACES $iface"
    fi
done
BLOCKED_IFACES=$(echo "$BLOCKED_IFACES" | xargs)

if [ -z "$BLOCKED_IFACES" ]; then
    echo "WARNING: All external interfaces are exempted. Nothing to block."
    exit 0
fi

echo ""
echo "Blocking forwarding from: $BLOCKED_IFACES"
echo "Protected subnets: $OCR_PROTECTED_NETS"
echo ""

# Add rules
for iface in $BLOCKED_IFACES; do
    for net in $OCR_PROTECTED_NETS; do
        add_rule "$iface" "$net" "$(subnet_label "$net")"
    done
done

# Save rules
echo ""
echo "Saving rules to /etc/iptables/rules.v4 ..."
if [ -d /etc/iptables ]; then
    iptables-save > /etc/iptables/rules.v4
    echo "Saved."
else
    echo "WARNING: /etc/iptables/ not found — rules are active but will not"
    echo "         persist across reboot. Mount -v /etc/iptables:/etc/iptables"
fi

echo ""
echo "=== Current DOCKER-USER rules (first 20) ==="
iptables -L DOCKER-USER -n -v --line-numbers 2>/dev/null | head -22
echo ""
echo "=== Done ==="
