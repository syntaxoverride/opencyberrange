#!/bin/bash
# ============================================================================
# Template-aware firewall entrypoint.
#
# Reads per-instance secrets from the environment with baked fallbacks:
#   CRED_analyst_USER  firewall SSH username  (fallback: analyst)
#   CRED_analyst_PASS  firewall SSH password  (fallback: M3r1d14n_Fw#)
#   FLAG               flag value             (fallback: OCR{tr4ff1c_c0ntr0ll3d})
#
# CRED_analyst_* are valid shell identifiers, so ${...} expansion is fine.
# All expansions are quoted to avoid word-splitting on special characters.
# ============================================================================
set -u

ANALYST_USER="${CRED_analyst_USER:-analyst}"
ANALYST_PASS="${CRED_analyst_PASS:-M3r1d14n_Fw#}"
# Two-step fallback: a brace-containing default inside ${FLAG:-...} mis-parses
# (the inner } closes the expansion early and a stray } leaks into the value), so
# assign the literal separately, single-quoted.
FLAG_VALUE="${FLAG:-}"
[ -n "$FLAG_VALUE" ] || FLAG_VALUE='OCR{tr4ff1c_c0ntr0ll3d}'

# Create the requested user if it differs from the baked default, then set the
# password and grant passwordless sudo (needed for iptables, monitor, check-rules).
if [ "$ANALYST_USER" != "analyst" ]; then
    useradd -m -s /bin/bash "$ANALYST_USER" 2>/dev/null || true
    usermod -aG sudo "$ANALYST_USER" 2>/dev/null || true
    echo "${ANALYST_USER} ALL=(ALL) NOPASSWD: ALL" > "/etc/sudoers.d/${ANALYST_USER}"
    chmod 0440 "/etc/sudoers.d/${ANALYST_USER}"
fi
echo "${ANALYST_USER}:${ANALYST_PASS}" | chpasswd

# Write the flag (revealed only by check-rules once the rules are correct).
echo "$FLAG_VALUE" > /root/flag.txt
chmod 600 /root/flag.txt

# Enable IP forwarding so this box acts as a router/firewall.
echo 1 > /proc/sys/net/ipv4/ip_forward

# Start SSH in the foreground.
exec /usr/sbin/sshd -D
