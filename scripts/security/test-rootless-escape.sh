#!/usr/bin/env bash
#
# Rootless / userns acceptance test (S1 follow-on).
#
# Simulates the worst case: the backend is compromised and creates a container
# with the host filesystem bind-mounted, then tries to write a root-owned file
# on the host. On a plain rootful daemon this succeeds (container-root ==
# host-root == full escape). Under userns-remap or rootless Docker the container's
# root maps to an unprivileged subuid, so the write to a real-root-owned path is
# denied.
#
# Run it on the lab host BEFORE and AFTER enabling userns-remap/rootless:
#   BEFORE -> expect FAIL (escape possible; that is the gap you are closing)
#   AFTER  -> expect PASS (escape closed)
#
# Exit code: 0 = PASS (blocked), 1 = FAIL (escape possible), 2 = test error.
# Safe + self-cleaning: writes only a marker file and removes it.
#
set -uo pipefail

IMG="${OCR_TEST_IMAGE:-alpine:3.19}"
MARK="/.ocr-escape-test-$$"          # target the host root dir (owned by uid 0)
HOSTMARK="/host${MARK}"

command -v docker >/dev/null 2>&1 || { echo "[rootless-escape] ERROR: docker not found"; exit 2; }

cleanup() {
  # remove the marker via a container mount so it works whether or not the
  # caller is root and regardless of the file's owner uid.
  docker run --rm -v /:/host "$IMG" sh -c "rm -f '$HOSTMARK' 2>/dev/null" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[rootless-escape] creating a container with -v /:/host and attempting a host-root write ..."
docker run --rm -v /:/host "$IMG" sh -c "echo pwned > '$HOSTMARK'" >/dev/null 2>&1 || true

# Did a root-owned file actually land on the host root dir?
owner="$(docker run --rm -v /:/host "$IMG" sh -c "stat -c %u '$HOSTMARK' 2>/dev/null" 2>/dev/null | tr -dc '0-9')"

if [ -n "$owner" ] && [ "$owner" = "0" ]; then
  echo "[rootless-escape] FAIL: a container wrote a uid-0 file at ${MARK} on the host."
  echo "                 Container-root == host-root -> a backend RCE can escape to host root."
  echo "                 Fix: enable userns-remap (or rootless Docker) and re-run; expect PASS."
  exit 1
fi

if [ -n "$owner" ]; then
  # A file exists but is owned by a non-zero (remapped) uid: the write landed as
  # an unprivileged subuid, i.e. userns is active. Still a PASS (not host root).
  echo "[rootless-escape] PASS: the write landed as remapped uid ${owner}, not host root. Escape closed."
  exit 0
fi

echo "[rootless-escape] PASS: the container could not write a root-owned file on the host. Escape closed."
exit 0
