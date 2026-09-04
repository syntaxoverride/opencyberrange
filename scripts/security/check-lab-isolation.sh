#!/usr/bin/env bash
#
# Lab-isolation acceptance check (S2), boot/CI-friendly.
#
# Asserts the lab -> host and lab -> management blocks are actually in force on
# this host, in two layers:
#
#   static  Verify the iptables rules that apply-lab-isolation.sh installs are
#           present: for every lab CIDR an INPUT DROP (lab -> host) and a
#           DOCKER-USER DROP to the infra bridge pool (lab -> management), plus
#           the ESTABLISHED/RELATED accepts that keep backend-initiated flows
#           alive. No containers started; runs in under a second, so it is safe
#           as a boot-time gate.
#   probe   Behavioral test: delegate to test-lab-isolation.sh, which stands up
#           a throwaway container on a lab-style subnet and proves it cannot
#           reach the backend, the DB, or the host via the bridge gateway.
#           Needs Docker up and the stack running.
#
# Usage:
#   check-lab-isolation.sh            static check (default; boot-safe)
#   check-lab-isolation.sh probe      live probe only
#   check-lab-isolation.sh full       static, then probe
#
# Exit code: 0 = PASS, 1 = FAIL (isolation not in force), 2 = check error.
#
# Wiring it in:
#   Boot: add a drop-in to the unit the installer creates, so a boot where the
#   rules failed to apply is loud instead of silently open:
#     sudo systemctl edit ocr-lab-isolation.service
#       [Service]
#       ExecStartPost=<install-dir>/scripts/security/check-lab-isolation.sh static
#   CI / post-deploy: run `check-lab-isolation.sh full` on the deployed host as
#   an acceptance step (the probe needs the stack up, so run it after
#   docker compose up -d).
#
# The rule model (marker, CIDR defaults, chain layout) mirrors
# apply-lab-isolation.sh in this directory; override LAB_CIDRS / INFRA_POOL the
# same way if you overrode them there.
#
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MARKER="ocr-lab-iso"
# Keep in sync with apply-lab-isolation.sh (same default lab + shared-VM model).
LAB_CIDRS="${LAB_CIDRS:-10.50.0.0/16 10.100.0.0/14 10.104.0.0/13 10.112.0.0/12 10.128.0.0/9}"
INFRA_POOL="${INFRA_POOL:-172.16.0.0/12}"
MODE="${1:-static}"

# iptables needs root; self-elevate like apply-lab-isolation.sh does.
if [ "$(id -u)" != 0 ] && { [ "$MODE" = "static" ] || [ "$MODE" = "full" ]; }; then
  exec sudo -E "$0" "$@"
fi

fail=0

static_check() {
  local input_rules docker_rules cidr ok
  command -v iptables >/dev/null 2>&1 || { echo "[check] ERROR: iptables not found"; exit 2; }
  input_rules=$(iptables -S INPUT 2>/dev/null | grep -F -- "$MARKER")
  docker_rules=$(iptables -S DOCKER-USER 2>/dev/null | grep -F -- "$MARKER")

  echo "[check] static rule assertions (marker: $MARKER)"
  if [ -z "$input_rules" ] && [ -z "$docker_rules" ]; then
    echo "  FAIL  no $MARKER rules installed at all."
    echo "        Apply them: sudo bash $HERE/apply-lab-isolation.sh apply"
    fail=1
    return
  fi

  for cidr in $LAB_CIDRS; do
    # lab -> host block
    if echo "$input_rules" | grep -q -- "-s $cidr .*-j DROP"; then
      echo "  ok    INPUT drops $cidr -> host"
    else
      echo "  FAIL  INPUT missing DROP for $cidr -> host"
      fail=1
    fi
    # lab -> management (infra bridge pool) block
    if echo "$docker_rules" | grep -q -- "-s $cidr -d $INFRA_POOL .*-j DROP"; then
      echo "  ok    DOCKER-USER drops $cidr -> $INFRA_POOL"
    else
      echo "  FAIL  DOCKER-USER missing DROP for $cidr -> $INFRA_POOL"
      fail=1
    fi
  done

  # The accepts that keep legitimate management-initiated traffic working. Their
  # absence does not open the isolation gap, but it breaks VNC/exec into labs,
  # so a boot with them missing is still a failed apply.
  # iptables -S may reorder the ctstate flag list, so match the pieces.
  if echo "$docker_rules" | grep -- "--ctstate" | grep -q -- "-j ACCEPT"; then
    echo "  ok    DOCKER-USER established/related accept present"
  else
    echo "  FAIL  DOCKER-USER established/related accept missing (partial apply)"
    fail=1
  fi
}

probe_check() {
  if [ ! -x "$HERE/test-lab-isolation.sh" ]; then
    echo "[check] ERROR: $HERE/test-lab-isolation.sh not found; cannot probe."
    echo "        This check assumes it sits next to apply-lab-isolation.sh in"
    echo "        scripts/security/ of the install folder."
    exit 2
  fi
  bash "$HERE/test-lab-isolation.sh" || fail=1
}

case "$MODE" in
  static) static_check ;;
  probe)  probe_check ;;
  full)   static_check; probe_check ;;
  *) echo "usage: $0 [static|probe|full]"; exit 2 ;;
esac

echo
if [ "$fail" -eq 0 ]; then
  echo "[check] PASS: lab isolation in force ($MODE)."
  exit 0
fi
echo "[check] FAIL: lab isolation NOT fully in force."
echo "        Reapply: sudo bash $HERE/apply-lab-isolation.sh apply"
echo "        Then rerun: $0 $MODE"
exit 1
