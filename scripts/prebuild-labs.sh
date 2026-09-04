#!/bin/bash
# ==============================================================================
# OpenCyberRange — Pre-build Lab Docker Images
# ==============================================================================
#
# Builds all lab Docker images ahead of time so student spawns are instant.
# Without pre-building, the first spawn triggers a full Docker build which
# can take minutes and hit the 120s timeout.
#
# USAGE:
#   ./scripts/prebuild-labs.sh                    # Build all labs
#   ./scripts/prebuild-labs.sh --track Windows    # Build one track
#   ./scripts/prebuild-labs.sh --lab windows-1-1-basic-port-scan  # Build one lab
#   ./scripts/prebuild-labs.sh --dry-run          # Show what would be built
#   ./scripts/prebuild-labs.sh --parallel 4       # Build 4 labs at a time
#
# ==============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LABS_DIR="$PROJECT_ROOT/labs"
LOG_DIR="$PROJECT_ROOT/scripts/.build-logs"

# Defaults
FILTER_TRACK=""
FILTER_LAB=""
DRY_RUN=false
PARALLEL=1
FORCE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --track)
            FILTER_TRACK="$2"
            shift 2
            ;;
        --lab)
            FILTER_LAB="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --parallel)
            PARALLEL="$2"
            shift 2
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Pre-build Docker images for all labs so student spawns are instant."
            echo ""
            echo "Options:"
            echo "  --track TRACK    Only build labs in this track directory (e.g., Windows, Web)"
            echo "  --lab SLUG       Only build a specific lab by slug"
            echo "  --parallel N     Build N labs concurrently (default: 1)"
            echo "  --force          Force rebuild even if image exists (--no-cache)"
            echo "  --dry-run        Show what would be built without building"
            echo "  -h, --help       Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Verify Docker is available
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed or not in PATH${NC}"
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not available${NC}"
    exit 1
fi

# --- Disk headroom -----------------------------------------------------------
# A full prebuild writes tens of GB of images + build cache. When the docker
# filesystem fills mid-run, image-layer and apt writes truncate, and apt then
# fails with the deeply misleading "At least one invalid signature was
# encountered" -- which looks like a network/GPG bug, not "no space left". So
# guard on free space up front AND before every build, and report it plainly.
DOCKER_ROOT="$(docker info -f '{{.DockerRootDir}}' 2>/dev/null || echo /var/lib/docker)"
CRITICAL_FREE_GB="${OCR_PREBUILD_MIN_FREE_GB:-10}"     # abort below this
RECOMMEND_FREE_GB="${OCR_PREBUILD_RECOMMEND_GB:-60}"   # warn below this
avail_gb() { df -BG --output=avail "$DOCKER_ROOT" 2>/dev/null | tail -1 | tr -dc '0-9'; }

# Create log directory
mkdir -p "$LOG_DIR"

echo ""
echo -e "${RED}${BOLD}     ██████╗  ██████╗██████╗ ${NC}"
echo -e "${RED}${BOLD}    ██╔═══██╗██╔════╝██╔══██╗${NC}"
echo -e "${YELLOW}${BOLD}    ██║   ██║██║     ██████╔╝${NC}"
echo -e "${GREEN}${BOLD}    ██║   ██║██║     ██╔══██╗${NC}"
echo -e "${CYAN}${BOLD}    ╚██████╔╝╚██████╗██║  ██║${NC}"
echo -e "${BLUE}${BOLD}     ╚═════╝  ╚═════╝╚═╝  ╚═╝${NC}"
echo ""
echo -e "${BOLD}${MAGENTA}    ╔═══════════════════════════════════════╗${NC}"
echo -e "${BOLD}${MAGENTA}    ║${NC}${BOLD}   O p e n C y b e r R a n g e         ${MAGENTA}║${NC}"
echo -e "${BOLD}${MAGENTA}    ║${NC}${DIM}   Pre-build Lab Images               ${MAGENTA}${BOLD}║${NC}"
echo -e "${BOLD}${MAGENTA}    ╚═══════════════════════════════════════╝${NC}"
echo ""

if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}DRY RUN MODE - No images will be built${NC}"
    echo ""
fi

# Collect labs to build
declare -a LABS_TO_BUILD=()

for track_dir in "$LABS_DIR"/*/; do
    track_name=$(basename "$track_dir")

    # Skip hidden directories
    [[ "$track_name" == .* ]] && continue

    # Filter by track if specified
    if [ -n "$FILTER_TRACK" ] && [ "$track_name" != "$FILTER_TRACK" ]; then
        continue
    fi

    for lab_dir in "$track_dir"*/; do
        lab_slug=$(basename "$lab_dir")

        # Skip hidden directories
        [[ "$lab_slug" == .* ]] && continue

        # Filter by specific lab if specified
        if [ -n "$FILTER_LAB" ] && [ "$lab_slug" != "$FILTER_LAB" ]; then
            continue
        fi

        # Must have docker-compose.yml
        if [ ! -f "$lab_dir/docker-compose.yml" ]; then
            continue
        fi

        LABS_TO_BUILD+=("$track_name|$lab_slug|$lab_dir")
    done
done

TOTAL=${#LABS_TO_BUILD[@]}

if [ "$TOTAL" -eq 0 ]; then
    echo -e "${YELLOW}No labs found to build.${NC}"
    if [ -n "$FILTER_TRACK" ]; then
        echo "  Track filter: $FILTER_TRACK"
    fi
    if [ -n "$FILTER_LAB" ]; then
        echo "  Lab filter: $FILTER_LAB"
    fi
    exit 0
fi

echo -e "Found ${GREEN}$TOTAL${NC} labs to build"
echo ""

# --- Order by curriculum so a backgrounded prebuild readies the labs students
#     hit first, first: Level 1 of every track, then Level 2, ... capstones last.
_lab_level() {
    case "$1" in
        *final*|*capstone*) echo 900 ;;
        *midterm*|*exam*)   echo 800 ;;
        *) local l; l=$(printf '%s' "$1" | grep -oE '\-[0-9]+\-' | head -1 | tr -d '-'); echo "${l:-500}" ;;
    esac
}
if [ "$DRY_RUN" != true ] && [ -z "$FILTER_LAB" ] && [ "$TOTAL" -gt 1 ]; then
    _keyed=()
    for _e in "${LABS_TO_BUILD[@]}"; do
        IFS='|' read -r _t _s _d <<< "$_e"
        _keyed+=("$(printf '%03d' "$(_lab_level "$_s")")|$_e")
    done
    IFS=$'\n' _sorted=($(printf '%s\n' "${_keyed[@]}" | sort)); unset IFS
    LABS_TO_BUILD=()
    for _e in "${_sorted[@]}"; do LABS_TO_BUILD+=("${_e#*|}"); done
fi

# --- Progress file the backend reads (/labs/.prebuild-progress.json) to show a
#     "still preparing" banner and gate spawns of not-yet-built labs. ---
PROGRESS_FILE="$LABS_DIR/.prebuild-progress.json"
_done_slugs=(); _failed_slugs=()
_json_array() { if [ "$#" -eq 0 ]; then echo "[]"; else local o; o=$(printf '"%s",' "$@"); echo "[${o%,}]"; fi; }
write_progress() {
    [ "$DRY_RUN" = true ] && return 0
    printf '{"total":%d,"done_count":%d,"done":%s,"failed":%s,"building":"%s","complete":%s}\n' \
        "$TOTAL" "${#_done_slugs[@]}" "$(_json_array "${_done_slugs[@]}")" \
        "$(_json_array "${_failed_slugs[@]}")" "${1:-}" "${2:-false}" \
        > "$PROGRESS_FILE" 2>/dev/null || true
}
write_progress "" false

# --- Disk preflight: fail fast with a plain message, not 60 cryptic GPG errors
if [ "$DRY_RUN" != true ]; then
    FREE_NOW=$(avail_gb)
    if [ -n "$FREE_NOW" ]; then
        echo -e "Disk: ${FREE_NOW}G free on ${DOCKER_ROOT}"
        if [ "$FREE_NOW" -lt "$CRITICAL_FREE_GB" ]; then
            echo -e "${RED}${BOLD}Not enough disk to build.${NC} Only ${FREE_NOW}G free on ${DOCKER_ROOT}"
            echo -e "${RED}(floor ${CRITICAL_FREE_GB}G). A full prebuild needs tens of GB; on a full disk"
            echo -e "the builds corrupt and apt fails with a misleading \"invalid signature\" error.${NC}"
            echo -e "${YELLOW}Free space (docker builder prune -af) or grow the disk, then re-run.${NC}"
            exit 1
        fi
        if [ "$FREE_NOW" -lt "$RECOMMEND_FREE_GB" ]; then
            echo -e "${YELLOW}WARNING: ${FREE_NOW}G free is below the recommended ${RECOMMEND_FREE_GB}G for a"
            echo -e "full prebuild. It may run out partway; watch for a disk-space stop below.${NC}"
        fi
        echo ""
    fi
fi

# Build function for a single lab
build_lab() {
    local track_name="$1"
    local lab_slug="$2"
    local lab_dir="$3"
    local index="$4"
    local total="$5"
    local log_file="$LOG_DIR/${lab_slug}.log"

    if [ "$DRY_RUN" = true ]; then
        echo -e "  [${index}/${total}] ${BLUE}Would build:${NC} ${track_name}/${lab_slug}"
        return 0
    fi

    echo -e "  [${index}/${total}] ${BLUE}Building:${NC} ${track_name}/${lab_slug}..."

    local build_args=("docker" "compose" "-f" "$lab_dir/docker-compose.yml" "-p" "prebuild-${lab_slug}" "build")

    if [ "$FORCE" = true ]; then
        build_args+=("--no-cache")
    fi

    if "${build_args[@]}" > "$log_file" 2>&1; then
        echo -e "  [${index}/${total}] ${GREEN}OK${NC}     ${track_name}/${lab_slug}"
        return 0
    else
        echo -e "  [${index}/${total}] ${RED}FAILED${NC} ${track_name}/${lab_slug}"
        echo -e "           ${YELLOW}Log: $log_file${NC}"
        return 1
    fi
}

# Build labs
SUCCESS=0
FAILED=0
FAILED_LABS=()

DISK_ABORT=false
for i in "${!LABS_TO_BUILD[@]}"; do
    IFS='|' read -r track_name lab_slug lab_dir <<< "${LABS_TO_BUILD[$i]}"
    index=$((i + 1))

    # Stop BEFORE the disk fills. A truncated image/apt write does not just fail
    # the current lab -- it corrupts silently and surfaces as apt "invalid
    # signature" on every following build. A clean stop with a real reason beats
    # dozens of red herrings.
    if [ "$DRY_RUN" != true ]; then
        FREE_NOW=$(avail_gb)
        if [ -n "$FREE_NOW" ] && [ "$FREE_NOW" -lt "$CRITICAL_FREE_GB" ]; then
            echo ""
            echo -e "${RED}${BOLD}Out of disk: ${FREE_NOW}G free on ${DOCKER_ROOT} (floor ${CRITICAL_FREE_GB}G).${NC}"
            echo -e "${YELLOW}Stopped after ${SUCCESS}/${TOTAL} built to avoid corrupt images and the"
            echo -e "misleading apt \"invalid signature\" cascade a full disk causes. Reclaim space"
            echo -e "(docker builder prune -af) or grow the disk, then re-run to finish the rest.${NC}"
            DISK_ABORT=true
            break
        fi
    fi

    write_progress "$lab_slug" false
    if build_lab "$track_name" "$lab_slug" "$lab_dir" "$index" "$TOTAL"; then
        SUCCESS=$((SUCCESS + 1))
        _done_slugs+=("$lab_slug"); write_progress "" false
    else
        FAILED=$((FAILED + 1))
        FAILED_LABS+=("$track_name/$lab_slug")
        _failed_slugs+=("$lab_slug"); write_progress "" false
    fi
done
# Mark the run complete (whether all built or a disk-abort stopped it) so the
# backend stops gating spawns / showing the banner for what did build.
write_progress "" true

# Summary
echo ""
echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}  Build Summary${NC}"
echo -e "${BLUE}==========================================${NC}"
echo ""

if [ "$DRY_RUN" = true ]; then
    echo -e "  Would build: ${TOTAL} labs"
else
    echo -e "  Total:   ${TOTAL}"
    echo -e "  ${GREEN}Success: ${SUCCESS}${NC}"
    if [ "$FAILED" -gt 0 ]; then
        echo -e "  ${RED}Failed:  ${FAILED}${NC}"
        echo ""
        echo -e "  ${RED}Failed labs:${NC}"
        for lab in "${FAILED_LABS[@]}"; do
            echo -e "    - $lab"
        done
        echo ""
        echo -e "  Build logs: $LOG_DIR/"
    fi
fi

echo ""

# Reclaim the BuildKit cache: once the images exist the cache is pure overhead
# and is the main reason the prebuild footprint balloons far past the image
# sizes. Pruning it here keeps the persistent footprint to just the images.
if [ "$DRY_RUN" != true ]; then
    echo -e "Reclaiming build cache (keeps the on-disk footprint to the images only)..."
    docker builder prune -f >/dev/null 2>&1 || true
    LEFT=$(avail_gb); [ -n "$LEFT" ] && echo -e "  ${LEFT}G free on ${DOCKER_ROOT} after prune."
    echo ""
fi

# Exit non-zero if any build failed OR we stopped on disk, so the installer warns.
if [ "$FAILED" -gt 0 ] || [ "$DISK_ABORT" = true ]; then
    exit 1
fi
