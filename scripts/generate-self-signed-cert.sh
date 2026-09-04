#!/usr/bin/env bash
# generate-self-signed-cert.sh — Create a self-signed TLS certificate for LAN deployments.
#
# Usage:
#   sudo bash scripts/generate-self-signed-cert.sh [HOSTNAME_OR_IP]
#
# If no argument is given, the script auto-detects the server's primary IP.
# Certificates are written to platform/certs/ and picked up by docker-compose
# via a volume mount. Restart the frontend container after generating:
#
#   cd platform && docker compose up -d frontend
#
set -euo pipefail

# Where the frontend compose mounts /etc/nginx/certs from. The caller sets
# OCR_CERT_DIR to the platform dir's certs/; default keeps standalone use
# working. Do not fall back to the current directory -- that silently wrote
# the cert wherever the script happened to run and HTTPS never came up.
CERT_DIR="${OCR_CERT_DIR:-$(cd "$(dirname "$0")/.." && pwd)/platform/certs}"
mkdir -p "$CERT_DIR"

# Determine hostname / IP
if [ -n "${1:-}" ]; then
    HOSTNAME="$1"
else
    HOSTNAME=$(hostname -I 2>/dev/null | awk '{print $1}')
    if [ -z "$HOSTNAME" ]; then
        echo "ERROR: Could not detect server IP. Pass it as an argument:" >&2
        echo "  sudo bash scripts/generate-self-signed-cert.sh 192.168.1.50" >&2
        exit 1
    fi
fi

echo "Generating self-signed TLS certificate for: $HOSTNAME"

# Create OpenSSL config with SAN (browsers require SAN, not just CN)
OPENSSL_CNF=$(mktemp)
cat > "$OPENSSL_CNF" <<SSLEOF
[req]
default_bits       = 2048
prompt             = no
default_md         = sha256
distinguished_name = dn
x509_extensions    = v3_ext

[dn]
CN = $HOSTNAME
O  = OpenCyberRange
OU = Self-Signed

[v3_ext]
subjectAltName      = @alt_names
basicConstraints    = critical, CA:FALSE
keyUsage            = digitalSignature, keyEncipherment
extendedKeyUsage    = serverAuth

[alt_names]
DNS.1 = $HOSTNAME
DNS.2 = localhost
IP.1  = $HOSTNAME
IP.2  = 127.0.0.1
SSLEOF

# If HOSTNAME is not an IP, remove the IP.1 line to avoid openssl error
if ! echo "$HOSTNAME" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$'; then
    sed -i '/^IP\.1/d' "$OPENSSL_CNF"
fi

openssl req -x509 -nodes -days 365 \
    -newkey rsa:2048 \
    -keyout "$CERT_DIR/selfsigned.key" \
    -out "$CERT_DIR/selfsigned.crt" \
    -config "$OPENSSL_CNF" 2>/dev/null

rm -f "$OPENSSL_CNF"

chmod 600 "$CERT_DIR/selfsigned.key"
chmod 644 "$CERT_DIR/selfsigned.crt"

echo ""
echo "Certificates written to:"
echo "  $CERT_DIR/selfsigned.crt"
echo "  $CERT_DIR/selfsigned.key"
echo ""
echo "Next steps:"
echo "  cd platform && docker compose up -d frontend"
echo ""
echo "The frontend will serve HTTPS on port 443 and redirect HTTP → HTTPS."
echo "Browsers will show a certificate warning — accept it or import selfsigned.crt"
echo "into your system trust store."
