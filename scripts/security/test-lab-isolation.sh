#!/usr/bin/env bash
#
# Lab-isolation acceptance test (S2).
#
# Stands up a throwaway probe container on a lab-style subnet (10.100.x, the same
# range real labs use) and checks it CANNOT reach the platform management plane:
# the backend, the database, the SIEM indexer, the host (via the bridge gateway),
# and -- optionally -- another tenant's lab subnet.
#
# Note on the baseline: Docker's default bridge isolation already keeps a lab off
# the management *containers* (they sit on a separate bridge). The vector that
# stays open is lab -> HOST: the bridge gateway (subnet .1) is the host, so any
# 0.0.0.0-bound host service (e.g. SSH) is reachable until DOCKER-USER drops it.
#
# Run on the lab host BEFORE and AFTER applying the DOCKER-USER firewall rules:
#   BEFORE -> expect FAIL (lab reaches the host via the gateway; that is the gap)
#   AFTER  -> expect PASS (every management target unreachable)
#
# Targets auto-detect from the running stack; override via env:
#   OCR_BACKEND_IP  OCR_BACKEND_PORT(=8000)
#   OCR_DB_IP       OCR_DB_PORT(=5432)
#   OCR_SIEM_IP     OCR_SIEM_PORT(=9200)   (leave OCR_SIEM_IP empty to skip)
#   OCR_PROBE_SUBNET(=10.100.250.0/24)     OCR_TENANT_IP (optional cross-tenant)
#
# Exit code: 0 = PASS (isolated), 1 = FAIL (management reachable), 2 = test error.
#
set -uo pipefail

IMG="${OCR_TEST_IMAGE:-alpine:3.19}"
NET="ocr-isolation-probe-$$"
SUBNET="${OCR_PROBE_SUBNET:-10.100.250.0/24}"

command -v docker >/dev/null 2>&1 || { echo "[lab-isolation] ERROR: docker not found"; exit 2; }

first_ip() { docker inspect "$1" --format '{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}' 2>/dev/null | awk '{print $1}'; }
BACKEND_IP="${OCR_BACKEND_IP:-$(first_ip ocr-backend)}"; BACKEND_PORT="${OCR_BACKEND_PORT:-8000}"
DB_IP="${OCR_DB_IP:-$(first_ip ocr-db)}";               DB_PORT="${OCR_DB_PORT:-5432}"
SIEM_IP="${OCR_SIEM_IP:-}";                              SIEM_PORT="${OCR_SIEM_PORT:-9200}"
TENANT_IP="${OCR_TENANT_IP:-}"

cleanup() { docker network rm "$NET" >/dev/null 2>&1 || true; }
trap cleanup EXIT

docker network create --subnet "$SUBNET" "$NET" >/dev/null 2>&1 \
  || { echo "[lab-isolation] ERROR: could not create probe network $SUBNET (subnet in use?)"; exit 2; }

# Returns 0 (reachable) if a TCP connect to ip:port succeeds within 2s.
reachable() {
  docker run --rm --network "$NET" "$IMG" sh -c "nc -z -w2 '$1' '$2'" >/dev/null 2>&1
}

fail=0
check() {  # name  ip  port
  local name="$1" ip="$2" port="$3"
  if [ -z "$ip" ]; then echo "  SKIP  $name (no IP)"; return; fi
  if reachable "$ip" "$port"; then
    echo "  FAIL  $name reachable from a lab subnet ($ip:$port)"
    fail=1
  else
    echo "  ok    $name unreachable ($ip:$port)"
  fi
}

# The bridge gateway (subnet .1) is the host's address on this network. A lab
# reaching a host service (e.g. SSH) through it means lab -> host is open.
GW="${OCR_HOST_GW:-$(echo "$SUBNET" | sed 's#\.0/[0-9]*$#.1#')}"

echo "[lab-isolation] probing the management plane from a container on $SUBNET ..."
check "backend"          "$BACKEND_IP" "$BACKEND_PORT"
check "database"         "$DB_IP"      "$DB_PORT"
check "SIEM indexer"     "$SIEM_IP"    "$SIEM_PORT"
check "host via gateway" "$GW"         "${OCR_HOST_SSH_PORT:-22}"
[ -n "$TENANT_IP" ] && check "another tenant lab" "$TENANT_IP" "${OCR_TENANT_PORT:-22}"

echo
if [ "$fail" -eq 0 ]; then
  echo "[lab-isolation] PASS: no management target reachable from the lab subnet."
  exit 0
fi
echo "[lab-isolation] FAIL: a lab subnet can reach the management plane."
echo "                Apply the DOCKER-USER rules (drop 10.100.0.0/16 -> mgmt) and re-run."
exit 1
