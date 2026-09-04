#!/bin/bash
# ============================================================================
# Template-aware entrypoint for the SSH File Discovery target.
#
# Reads per-instance secrets from the environment with baked fallbacks so the
# image runs identically whether or not the platform injects values:
#   CRED_ssh-user_USER  SSH username   (fallback: webadmin)
#   CRED_ssh-user_PASS  SSH password   (fallback: WebServer2024#)
#   FLAG                flag value     (fallback: OCR{f1l3_d1sc0v3ry})
#
# The credential env vars contain a hyphen, which is not a valid POSIX shell
# identifier, so they are read with printenv rather than ${...} expansion.
# All expansions are quoted to avoid word-splitting on special characters.
# ============================================================================
set -u

SSH_USER="$(printenv 'CRED_ssh-user_USER' 2>/dev/null || true)"
SSH_USER="${SSH_USER:-webadmin}"
SSH_PASS="$(printenv 'CRED_ssh-user_PASS' 2>/dev/null || true)"
SSH_PASS="${SSH_PASS:-WebServer2024#}"
# Two-step fallback: a brace-containing default inside ${FLAG:-...} mis-parses
# (the inner } closes the expansion early and a stray } leaks into the value), so
# assign the literal separately, single-quoted.
FLAG_VALUE="${FLAG:-}"
[ -n "$FLAG_VALUE" ] || FLAG_VALUE='OCR{f1l3_d1sc0v3ry}'

# Create the requested user if it differs from the baked default.
if [ "$SSH_USER" != "webadmin" ]; then
    useradd -m -s /bin/bash "$SSH_USER" 2>/dev/null || true
fi
echo "${SSH_USER}:${SSH_PASS}" | chpasswd

# Write the flag into the deployment notes file the tester reads.
mkdir -p /var/www/html/backups
cat > /var/www/html/backups/deployment_notes.txt <<EOF
================================================================================
                      Web Portal Deployment Notes
================================================================================

Deployment Date: 2026-01-04
Deployed By: ${SSH_USER}
Version: 2.1.4

Configuration Changes:
- Updated database credentials
- Enabled debug mode for troubleshooting (TODO: disable in production)

Known Issues:
- Debug mode still enabled
- Old config backup files in backups/ directory (should be removed)

Security Assessment Flag: ${FLAG_VALUE}

================================================================================
EOF
chmod 644 /var/www/html/backups/deployment_notes.txt

# Generate host keys if missing, then start sshd in the foreground.
ssh-keygen -A 2>/dev/null
exec /usr/sbin/sshd -D -e
