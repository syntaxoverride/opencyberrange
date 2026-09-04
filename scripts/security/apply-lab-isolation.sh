#!/usr/bin/env bash
#
# Lab -> management-plane isolation rules (S2). Applies to ALL editions
# (Lite, Lite-SOC, Enterprise); Enterprise's shared VMs are covered too.
#
# Closes the gap the isolation acceptance test finds: a lab/shared-VM container
# can reach the HOST via its bridge gateway (e.g. host SSH), and -- as
# defense-in-depth over Docker's bridge isolation -- must not reach the
# management containers (backend / db).
#
# SUBNET MODEL (from docker_manager.py _LAB_SUBNETS + shared containers):
#   Lab + shared-VM traffic sources: 10.50/16, 10.100/14, 10.104/13, 10.112/12,
#   10.128/9 (the last covers 10.150/24 shared VMs AND, awkwardly, the SIEM
#   subnets 10.200/10.201). So we ACCEPT the detected management sources FIRST,
#   then drop the broad lab ranges -- otherwise the SIEM, which lives inside the
#   lab range, would be blocked from the host.
#
# Two chains do the work:
#   INPUT        drop lab-sourced traffic to the host itself (the real open gap;
#                container -> host is INPUT, not FORWARD). Management sources are
#                accepted first so SIEM/backend are not caught by the overlap.
#   DOCKER-USER  ESTABLISHED/RELATED accepted (so backend-initiated flows to labs
#                -- VNC, exec -- keep working), then NEW lab -> 172.16/12 (the
#                Docker bridge pool: backend/db and any infra bridge) dropped.
#                The SIEM subnets overlap the lab range, so lab -> SIEM is left to
#                Docker's proven bridge isolation rather than a risky source drop.
#
# Usage (needs root; self-elevates via sudo):
#   apply-lab-isolation.sh            apply the rules (idempotent)
#   apply-lab-isolation.sh remove     remove them
#   apply-lab-isolation.sh status     show the currently-installed marker rules
#
# Override via env:
#   LAB_CIDRS  (space-separated lab source ranges; default = the model above)
#   MGMT_CIDRS (space-separated management subnets to protect; auto-detected)
#   INFRA_POOL (Docker bridge pool to shield in DOCKER-USER; default 172.16.0.0/12)
#
# NOTE ON PERSISTENCE: iptables rules do not survive a reboot, and Docker
# recreates DOCKER-USER empty when the daemon restarts. The installer wires this
# into ocr-lab-isolation.service so it reapplies on boot + docker restart.
#
set -uo pipefail

[ "$(id -u)" = 0 ] || exec sudo -E "$0" "$@"

MARKER="ocr-lab-iso"
# Full lab + shared-VM source model. 10.128/9 includes 10.150/24 (shared VMs).
LAB_CIDRS="${LAB_CIDRS:-10.50.0.0/16 10.100.0.0/14 10.104.0.0/13 10.112.0.0/12 10.128.0.0/9}"
INFRA_POOL="${INFRA_POOL:-172.16.0.0/12}"

# ── Internet egress block (S3) ────────────────────────────────────────────
# Students must not reach the internet FROM a lab, RangeBox, or shared VM: an
# acceptable-use violation launched from the range traces back to this site's
# public IP.
#
# Blocking 10/8 wholesale rather than enumerating ranges is deliberate. The
# platform allocates lab/RangeBox/shared-VM subnets across 10.50, 10.100-10.127,
# 10.150 and 10.152, and a new allocator (the DFIR RangeBox on 10.152 was
# exactly this) would otherwise silently get egress. Deny-by-default, then
# carve out the few 10.x ranges that legitimately need out.
EGRESS_CIDRS="${EGRESS_CIDRS:-10.0.0.0/8}"
# 10.x ranges that KEEP egress. The SIEM pulls rule/CTI updates and lives
# inside the lab range, so it must be excepted explicitly.
EGRESS_ALLOW="${EGRESS_ALLOW:-10.200.0.0/24 10.201.0.0/24}"
# External interface to block toward; auto-detected from the default route.
EXT_IF="${EXT_IF:-$(ip route show default 2>/dev/null | awk '/default/{print $5; exit}')}"
ACTION="${1:-apply}"

# Auto-detect management subnets to PROTECT (accept their host-bound traffic even
# though 10.200/10.201 fall inside the lab range): the backend/db compose bridge
# plus any 10.20x SIEM network. Override wholesale with MGMT_CIDRS="a b c".
#
# The compose bridge is identified by its subnet sitting in the Docker bridge
# pool (INFRA_POOL, 172.16/12), NOT by being the container's first network. The
# backend is attached to lab and shared-VM networks as well, and their order
# changes as sessions come and go: picking the first one spared whichever lab
# subnet happened to sort first, which would have opened the whole shared
# Windows VM range (10.150/24) to the host. Individual management addresses are
# handled by detect_mgmt_hosts below, so nothing is lost by being strict here.
detect_mgmt() {
  local out="" net sub
  for c in ocr-backend ocr-db; do
    for net in $(docker inspect "$c" \
      --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}' 2>/dev/null); do
      sub=$(docker network inspect "$net" \
        --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}' 2>/dev/null)
      case "$sub" in
        172.1[6-9].*|172.2[0-9].*|172.3[0-1].*) out="$out $sub" ;;
      esac
    done
  done
  for n in $(docker network ls --format '{{.Name}}' 2>/dev/null); do
    sub=$(docker network inspect "$n" --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}' 2>/dev/null)
    case "$sub" in 10.200.*|10.201.*) out="$out $sub";; esac
  done
  echo "$out" | tr ' ' '\n' | awk 'NF && !seen[$0]++' | tr '\n' ' '
}
MGMT_CIDRS="${MGMT_CIDRS:-$(detect_mgmt)}"

# Management HOST addresses to spare, as /32s.
#
# detect_mgmt above only spares the backend's FIRST network. That is not enough.
# The backend is also attached to lab networks so it can reach lab containers,
# and Docker picks the default gateway from the alphabetically first attachment
# when the container restarts -- "ocr-rangebox-standalone-NN" sorts ahead of
# "ocr_default". A routine restart therefore moves the backend's default route
# onto a lab network, after which every host-bound and internet-bound packet
# leaves with a lab source address and the rules below drop it.
#
# Sparing the containers' individual addresses keeps isolation intact: the rest
# of each lab subnet is still dropped, and no lab container gains anything. The
# list is re-detected on every apply, so it self-heals when addresses change.
detect_mgmt_hosts() {
  local out="" c a addrs
  for c in ocr-backend ocr-db; do
    addrs=$(docker inspect "$c" \
      --format '{{range $k,$v := .NetworkSettings.Networks}}{{$v.IPAddress}} {{end}}' \
      2>/dev/null)
    for a in $addrs; do
      [ -n "$a" ] && out="$out $a/32"
    done
  done
  echo "$out" | tr ' ' '\n' | awk 'NF && !seen[$0]++' | tr '\n' ' '
}
MGMT_HOSTS="${MGMT_HOSTS:-$(detect_mgmt_hosts)}"

ins() {  # ins CHAIN POS "piped|spec"
  local chain="$1" pos="$2"; shift 2
  local IFS='|'; read -ra spec <<< "$1"
  iptables -I "$chain" "$pos" "${spec[@]}"
}

# All rule specs, chain-tagged "CHAIN piped|spec", newest-on-top insert order:
# emit DROPs before ACCEPTs so the ACCEPTs end up above them after -I at pos 1.
all_specs() {
  local cidr
  # INPUT drops (lab -> host) -- inserted first, so they sink to the bottom.
  for cidr in $LAB_CIDRS; do
    echo "INPUT -s|$cidr|-j|DROP|-m|comment|--comment|$MARKER"
  done
  # INPUT established accept for lab sources (return traffic of host-initiated conns).
  for cidr in $LAB_CIDRS; do
    echo "INPUT -s|$cidr|-m|conntrack|--ctstate|ESTABLISHED,RELATED|-j|ACCEPT|-m|comment|--comment|$MARKER"
  done
  # INPUT accept management sources (protect SIEM/backend inside the lab range) -- on top.
  for cidr in $MGMT_CIDRS; do
    echo "INPUT -s|$cidr|-j|ACCEPT|-m|comment|--comment|$MARKER"
  done
  # The management containers' own addresses, whichever network they sit on.
  # Narrower than a subnet accept: these hosts only.
  for host in $MGMT_HOSTS; do
    echo "INPUT -s|$host|-j|ACCEPT|-m|comment|--comment|$MARKER"
  done
  # DOCKER-USER drops (NEW lab -> infra bridge pool) -- inserted first, sink to bottom.
  for cidr in $LAB_CIDRS; do
    echo "DOCKER-USER -s|$cidr|-d|$INFRA_POOL|-j|DROP|-m|comment|--comment|$MARKER"
  done
  # DOCKER-USER established accept -- on top, so backend-initiated flows to labs survive.
  echo "DOCKER-USER -m|conntrack|--ctstate|ESTABLISHED,RELATED|-j|ACCEPT|-m|comment|--comment|$MARKER"
  # DOCKER-USER internet-egress: broad DROP emitted first, per-range ACCEPTs
  # emitted last so they land ABOVE the DROP (specs are inserted at position 1,
  # so the last one emitted ends up on top).
  if [ -n "$EXT_IF" ]; then
    for cidr in $EGRESS_CIDRS; do
      echo "DOCKER-USER -s|$cidr|-o|$EXT_IF|-j|DROP|-m|comment|--comment|$MARKER"
    done
    for cidr in $EGRESS_ALLOW; do
      echo "DOCKER-USER -s|$cidr|-o|$EXT_IF|-j|ACCEPT|-m|comment|--comment|$MARKER"
    done
    # Emitted last so it lands above the broad drop: the management containers
    # keep egress even while holding a lab-network address. Spares only these
    # hosts, never a lab container, so the acceptable-use block on student
    # machines is unchanged.
    for host in $MGMT_HOSTS; do
      echo "DOCKER-USER -s|$host|-o|$EXT_IF|-j|ACCEPT|-m|comment|--comment|$MARKER"
    done
  fi
}

# Delete EVERY rule bearing our marker (not just the current spec set), so an
# apply after the rule shapes change (e.g. a widened LAB_CIDRS) cleans up stale
# rules too. The marker has no spaces, so `iptables -S` prints it unquoted and the
# line word-splits back into a valid `-D` delete.
strip() {
  local chain line
  for chain in INPUT DOCKER-USER; do
    while line=$(iptables -S "$chain" 2>/dev/null | grep -F -- "$MARKER" | head -1); [ -n "$line" ]; do
      iptables ${line/#-A/-D} 2>/dev/null || break
    done
  done
}
show() {
  echo "== INPUT ($MARKER) =="
  iptables -S INPUT 2>/dev/null | grep -F -- "$MARKER" || echo "  (none)"
  echo "== DOCKER-USER ($MARKER) =="
  iptables -S DOCKER-USER 2>/dev/null | grep -F -- "$MARKER" || echo "  (none)"
}

case "$ACTION" in
  status) show; exit 0 ;;
  remove) strip; echo "[lab-isolation] removed $MARKER rules."; show; exit 0 ;;
  apply)  ;;
  *) echo "usage: $0 [apply|remove|status]"; exit 2 ;;
esac

# Clean slate, then (re)install at position 1 in emit order -- idempotent.
strip
all_specs | while read -r chain spec; do ins "$chain" 1 "$spec"; done

echo "[lab-isolation] applied."
echo "  lab sources : $LAB_CIDRS"
echo "  mgmt spared : ${MGMT_CIDRS:-<none detected>}"
echo "  infra pool  : $INFRA_POOL (DOCKER-USER drop dest)"
echo
show
echo
echo "Validate with: scripts/security/test-lab-isolation.sh  (expect PASS;"
echo "  also try OCR_PROBE_SUBNET=10.150.99.0/24 for the shared-VM range)"
