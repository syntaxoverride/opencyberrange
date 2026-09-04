#!/usr/bin/env bash
#
# Enable Docker userns-remap (S1 follow-on: close container-create -> host-root).
#
# With userns-remap the container's root (uid 0) maps to an unprivileged subuid
# on the host, so a compromised backend that spawns `-v /:/host` can no longer
# write host-root files. Validate with scripts/security/test-rootless-escape.sh
# (FAIL before, PASS after).
#
# HARD PREREQUISITE -- no KVM/privileged workloads on this host:
#   userns-remap is daemon-wide and cannot grant the host root that KVM or
#   privileged containers need, so it BREAKS: the FWIDS labs (privileged +
#   /dev/kvm OPNsense VM) AND the Enterprise shared VMs (Dockur Windows, spawned
#   with /dev/kvm). It suits Lite / Lite-SOC, which have neither. The guard below
#   refuses when it detects privileged labs, /dev/kvm labs, or shared_vms:true in
#   the entitlement, unless OCR_ACK_FWIDS=1.
#
# COST -- userns-remap uses a SEPARATE storage root (/var/lib/docker/<uid>.<gid>),
#   so after `systemctl restart docker` the daemon starts with NO images/
#   containers/volumes: base images re-pull, lab images rebuild on first spawn,
#   and named volumes must be re-created/restored. Run in a maintenance window.
#
# Usage (needs root; self-elevates):
#   enable-userns-remap.sh --dry-run [outfile]   generate the merged daemon.json
#                                                 to a temp file and print it; the
#                                                 live daemon is untouched (safe).
#   enable-userns-remap.sh apply [--restart]      back up + write daemon.json;
#                                                 restart docker only with --restart.
#   enable-userns-remap.sh rollback               restore the most recent backup.
#
set -uo pipefail

DAEMON_JSON="/etc/docker/daemon.json"
BACKUP="${DAEMON_JSON}.ocr-bak"
REMAP_USER="${OCR_USERNS_USER:-default}"

MODE="${1:-}"; [ -n "$MODE" ] || { echo "usage: $0 [--dry-run [outfile] | apply [--restart] | rollback]"; exit 2; }

# --dry-run just writes a file; everything else needs root.
if [ "$MODE" != "--dry-run" ] && [ "$(id -u)" != 0 ]; then exec sudo -E "$0" "$@"; fi

# Produce the merged daemon.json on stdout: preserve an existing config (needs jq
# to merge safely) and set userns-remap. If a config exists and jq is missing,
# refuse rather than clobber unrelated daemon settings.
render_config() {
  if [ -s "$DAEMON_JSON" ]; then
    if command -v jq >/dev/null 2>&1; then
      jq --arg u "$REMAP_USER" '. + {"userns-remap":$u}' "$DAEMON_JSON"
    else
      echo "ERROR: $DAEMON_JSON already exists and jq is not installed to merge it safely." >&2
      echo "       Install jq, or add  \"userns-remap\": \"$REMAP_USER\"  to it by hand." >&2
      return 1
    fi
  else
    printf '{\n  "userns-remap": "%s"\n}\n' "$REMAP_USER"
  fi
}

hardware_guard() {
  # userns-remap cannot grant the host root that privileged labs or /dev/kvm
  # passthrough need. Three things break it, across dev tree and installed
  # artifact layouts:
  #   1. FWIDS labs         -- privileged: true in a compose
  #   2. any /dev/kvm lab   -- device passthrough (FWIDS, and future KVM labs)
  #   3. shared VMs         -- Dockur Windows is spawned in code with /dev/kvm;
  #                            the only static signal is shared_vms:true in the
  #                            edition entitlement.
  local labdirs="" d n_priv n_kvm shared=""
  for d in platform/labs labs; do [ -d "$d" ] && labdirs="$labdirs $d"; done
  n_priv=$(grep -rlE 'privileged:\s*true' $labdirs 2>/dev/null | wc -l | tr -d ' ')
  n_kvm=$(grep -rl '/dev/kvm' $labdirs 2>/dev/null | wc -l | tr -d ' ')
  for e in backend/data/entitlement.json backend/app/data/entitlement.json platform/backend/data/entitlement.json; do
    [ -f "$e" ] && grep -qE '"shared_vms"\s*:\s*true' "$e" && shared="yes"
  done
  if { [ "${n_priv:-0}" != 0 ] || [ "${n_kvm:-0}" != 0 ] || [ -n "$shared" ]; } && [ "${OCR_ACK_FWIDS:-0}" != 1 ]; then
    echo "REFUSING: this host/edition needs the rootful daemon -- userns-remap will break it:" >&2
    [ "${n_priv:-0}" != 0 ] && echo "          - $n_priv privileged (FWIDS) lab compose file(s)" >&2
    [ "${n_kvm:-0}"  != 0 ] && echo "          - $n_kvm lab(s) using /dev/kvm passthrough" >&2
    [ -n "$shared" ]        && echo "          - shared_vms:true (Enterprise Dockur Windows uses /dev/kvm)" >&2
    echo "          userns-remap suits Lite / Lite-SOC (no KVM). Set OCR_ACK_FWIDS=1 to override." >&2
    return 1
  fi
}

case "$MODE" in
  --dry-run)
    OUT="${2:-/tmp/ocr-daemon.json.preview}"
    render_config > "$OUT" || exit 1
    echo "[userns] dry-run: merged daemon.json written to $OUT (live daemon untouched)"
    echo "----------------------------------------------------------------------"
    cat "$OUT"
    echo "----------------------------------------------------------------------"
    command -v jq >/dev/null 2>&1 && { jq empty "$OUT" && echo "[userns] valid JSON"; }
    ;;
  apply)
    hardware_guard || exit 1
    [ -f "$DAEMON_JSON" ] && cp -a "$DAEMON_JSON" "$BACKUP" && echo "[userns] backed up $DAEMON_JSON -> $BACKUP"
    tmp="$(render_config)" || exit 1
    mkdir -p "$(dirname "$DAEMON_JSON")"
    printf '%s\n' "$tmp" > "$DAEMON_JSON"
    echo "[userns] wrote userns-remap=$REMAP_USER to $DAEMON_JSON"
    if [ "${2:-}" = "--restart" ]; then
      echo "[userns] restarting docker (storage root changes; images will re-pull) ..."
      systemctl restart docker
      echo "[userns] docker restarted. Validate: scripts/security/test-rootless-escape.sh (expect PASS)"
    else
      echo "[userns] NOT restarting. In a maintenance window run: systemctl restart docker"
      echo "         then re-pull base images / rebuild the stack, and validate with"
      echo "         scripts/security/test-rootless-escape.sh (expect PASS)."
    fi
    ;;
  rollback)
    if [ -f "$BACKUP" ]; then
      cp -a "$BACKUP" "$DAEMON_JSON"; echo "[userns] restored $DAEMON_JSON from $BACKUP"
    else
      rm -f "$DAEMON_JSON"; echo "[userns] no backup found; removed $DAEMON_JSON (was created by apply)"
    fi
    echo "[userns] restart docker to revert: systemctl restart docker"
    ;;
  *) echo "usage: $0 [--dry-run [outfile] | apply [--restart] | rollback]"; exit 2 ;;
esac
