#!/bin/bash
# ==============================================================================
# OpenCyberRange — Update Deployment
# ==============================================================================
#
# Pulls latest changes and applies platform updates (backend, frontend, DB).
# Typically called from setup-range-server.sh Update menu option.
#
# USAGE:
#   sudo bash deploy-updates.sh              # Deploy everything
#   sudo bash deploy-updates.sh --platform   # Deploy platform only
#   sudo bash deploy-updates.sh --dry-run    # Preview without changes
#
# ==============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m' # No Color

# Configuration
# Detect actual user's home directory even when running with sudo
if [ -n "$SUDO_USER" ]; then
    ACTUAL_HOME=$(getent passwd "$SUDO_USER" | cut -d: -f6)
else
    ACTUAL_HOME="$HOME"
fi
PLATFORM_DIR="${OCR_PLATFORM_DIR:-$ACTUAL_HOME/opencyberrange}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="$PLATFORM_DIR/.backups"
LOG_FILE="$REPO_DIR/scripts/deploy.log"
STATE_FILE="$REPO_DIR/scripts/.update-state"

# Default options
DEPLOY_PLATFORM=false
DRY_RUN=false
PREBUILD_IMAGES=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --platform|--vpn|--all)
            DEPLOY_PLATFORM=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --prebuild)
            PREBUILD_IMAGES=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Usage: $0 [--platform] [--all] [--dry-run]"
            exit 1
            ;;
    esac
done

# If no options specified, default to deploying everything
if [ "$DEPLOY_PLATFORM" = false ]; then
    DEPLOY_PLATFORM=true
fi

# Logging function
log() {
    echo -e "$1" | tee -a "$LOG_FILE"
}

# Error handling
error_exit() {
    log "${RED}ERROR: $1${NC}"
    exit 1
}

# Pre-flight checks
preflight_checks() {
    log "${BLUE}Running pre-flight checks...${NC}"
    
    # Check if running on server
    if [ ! -d "$PLATFORM_DIR" ]; then
        error_exit "Platform directory not found: $PLATFORM_DIR\nThis script must be run on the lab platform server."
    fi
    
    # Check if git repo (optional - ZIP downloads work too)
    if [ ! -d "$REPO_DIR/.git" ]; then
        log "${YELLOW}⚠ Not a git repository - assuming ZIP download${NC}"
        log "${YELLOW}  Make sure you've extracted the latest ZIP before running updates${NC}"
    fi
    
    # Check if docker is available
    if ! command -v docker &> /dev/null; then
        error_exit "Docker is not installed or not in PATH"
    fi
    
    # Check if docker compose is available
    if ! docker compose version &> /dev/null; then
        error_exit "Docker Compose is not available"
    fi
    
    # Check if we're in the platform directory for docker compose
    if [ ! -f "$PLATFORM_DIR/docker-compose.yml" ]; then
        error_exit "docker-compose.yml not found in $PLATFORM_DIR"
    fi
    
    log "${GREEN}✓ Pre-flight checks passed${NC}"
}

# Create backup
create_backup() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_path="$BACKUP_DIR/$timestamp"
    
    log "${BLUE}Creating backup at $backup_path...${NC}"
    
    if [ "$DRY_RUN" = true ]; then
        log "${YELLOW}[DRY RUN] Would create backup at $backup_path${NC}"
        return 0
    fi
    
    mkdir -p "$backup_path"
    
    # Backup critical files
    if [ -f "$PLATFORM_DIR/.env" ]; then
        cp "$PLATFORM_DIR/.env" "$backup_path/.env"
    fi
    
    if [ -d "$PLATFORM_DIR/backend" ]; then
        cp -r "$PLATFORM_DIR/backend" "$backup_path/backend"
    fi
    
    if [ -d "$PLATFORM_DIR/frontend" ]; then
        cp -r "$PLATFORM_DIR/frontend" "$backup_path/frontend"
    fi
    
    log "${GREEN}✓ Backup created${NC}"
    echo "$backup_path"
}

# Pull latest from git (or skip if ZIP download)
git_pull() {
    # Skip git pull if not a git repository (ZIP download)
    if [ ! -d "$REPO_DIR/.git" ]; then
        log "${YELLOW}⚠ Skipping git pull (not a git repository)${NC}"
        log "${YELLOW}  Assuming you've already extracted the latest ZIP${NC}"
        return 0
    fi
    
    log "${BLUE}Pulling latest changes from git...${NC}"
    
    if [ "$DRY_RUN" = true ]; then
        log "${YELLOW}[DRY RUN] Would run: git pull${NC}"
        return 0
    fi
    
    cd "$REPO_DIR"
    # Pull as the repo owner, not root. A root `git pull` writes root-owned
    # objects into the user's .git (and modern git refuses the pull outright as
    # "dubious ownership"), which then breaks the user's own later `git pull`.
    local git_ok=0
    if [ "$EUID" -eq 0 ] && [ -n "$SUDO_USER" ]; then
        sudo -u "$SUDO_USER" git pull && git_ok=1
    else
        git pull && git_ok=1
    fi
    # Restore ownership either way, in case a partial fetch touched .git as root.
    if [ "$EUID" -eq 0 ] && [ -n "$SUDO_USER" ]; then
        chown -R "$SUDO_USER:$SUDO_USER" "$REPO_DIR/.git" 2>/dev/null || true
    fi
    if [ "$git_ok" -ne 1 ]; then
        # A private or unreachable remote must not abort the whole update. The
        # local tree is a valid source: rebuild and restart from what is here.
        log "${YELLOW}⚠ Git pull failed (remote unreachable or private) — continuing with the local tree.${NC}"
        return 0
    fi
    
    log "${GREEN}✓ Git pull successful${NC}"
}

# Apply platform update
apply_platform_update() {
    log "${BLUE}Applying platform update...${NC}"
    
    if [ "$DRY_RUN" = true ]; then
        log "${YELLOW}[DRY RUN] Would copy platform files to $PLATFORM_DIR${NC}"
        return 0
    fi
    
    # Copy backend files
    # NOTE: rsync runs as root to handle root-owned __pycache__ files
    # created by Docker containers, then chown restores real user ownership.
    if [ -d "$REPO_DIR/platform/backend" ]; then
        log "Copying backend files..."
        if command -v rsync &> /dev/null; then
            rsync -rlpt --delete --exclude='__pycache__' "$REPO_DIR/platform/backend/" "$PLATFORM_DIR/backend/"
        else
            find "$REPO_DIR/platform/backend" -mindepth 1 -maxdepth 1 -exec cp -r {} "$PLATFORM_DIR/backend/" \;
        fi
        if [ "$EUID" -eq 0 ] && [ -n "$SUDO_USER" ]; then
            chown -R "$SUDO_USER:$SUDO_USER" "$PLATFORM_DIR/backend/"
        fi
    else
        error_exit "Platform backend directory not found"
    fi

    # Copy frontend files
    if [ -d "$REPO_DIR/platform/frontend" ]; then
        log "Copying frontend files..."
        if command -v rsync &> /dev/null; then
            # Never sync wiki/ from the repo. The deployed build context holds
            # the real wiki tree, built by platform/scripts/deploy-wiki.sh from
            # wikis.yaml and courses.json. The copy in the repo is a stale
            # fragment with no course/ or range/ subdirectory, so --delete would
            # take out every course and range wiki and the next image build
            # would bake the loss in. Course workbooks vanished this way once
            # already and it surfaced as a student unable to open a workbook.
            rsync -rlpt --delete --exclude='__pycache__' --exclude='wiki' \
                "$REPO_DIR/platform/frontend/" "$PLATFORM_DIR/frontend/"
        else
            # Same exclusion as the rsync path above: the repo's wiki/ is a
            # stale fragment and must not land on top of the built tree.
            find "$REPO_DIR/platform/frontend" -mindepth 1 -maxdepth 1 \
                -name wiki -prune -o -exec cp -r {} "$PLATFORM_DIR/frontend/" \;
        fi
        if [ "$EUID" -eq 0 ] && [ -n "$SUDO_USER" ]; then
            chown -R "$SUDO_USER:$SUDO_USER" "$PLATFORM_DIR/frontend/"
        fi
    else
        error_exit "Platform frontend directory not found"
    fi

    # Copy db files (ensure-db-password entrypoint wrapper)
    if [ -d "$REPO_DIR/platform/db" ]; then
        log "Copying db files..."
        mkdir -p "$PLATFORM_DIR/db"
        if command -v rsync &> /dev/null; then
            rsync -rlpt "$REPO_DIR/platform/db/" "$PLATFORM_DIR/db/"
        else
            cp -r "$REPO_DIR/platform/db/"* "$PLATFORM_DIR/db/" 2>/dev/null || true
        fi
        chmod +x "$PLATFORM_DIR/db/"*.sh 2>/dev/null || true
        if [ "$EUID" -eq 0 ] && [ -n "$SUDO_USER" ]; then
            chown -R "$SUDO_USER:$SUDO_USER" "$PLATFORM_DIR/db/"
        fi
    fi
    
    # Initialize database schema (idempotent - safe to run multiple times)
    if [ -f "$REPO_DIR/platform/scripts/init_database.sh" ]; then
        log "Initializing database schema..."
        cd "$PLATFORM_DIR"
        chmod +x "$REPO_DIR/platform/scripts/init_database.sh"
        bash "$REPO_DIR/platform/scripts/init_database.sh" || error_exit "Database initialization failed"
    fi
    
    # Fix ownership if scripts were previously created by root/Docker
    if [ -d "$PLATFORM_DIR/backend/app/scripts" ] && [ -n "$SUDO_USER" ]; then
        chown -R "$SUDO_USER:$SUDO_USER" "$PLATFORM_DIR/backend/app/scripts" 2>/dev/null || true
    fi
    
    log "${GREEN}✓ Platform update applied${NC}"
}


# Patch docker-compose.yml to add the db password sync entrypoint
# This is a one-time migration for installations created before this fix.
patch_docker_compose() {
    local compose_file="$PLATFORM_DIR/docker-compose.yml"

    if [ ! -f "$compose_file" ]; then
        return 0
    fi

    # Skip if already patched
    if grep -q "ensure-db-password.sh" "$compose_file" 2>/dev/null; then
        log "${GREEN}✓ docker-compose.yml already has password sync entrypoint${NC}"
        return 0
    fi

    log "Patching docker-compose.yml with db password sync entrypoint..."

    if [ "$DRY_RUN" = true ]; then
        log "${YELLOW}[DRY RUN] Would patch docker-compose.yml${NC}"
        return 0
    fi

    # Add entrypoint line after "container_name: ocr-db"
    sed -i '/container_name: ocr-db/a\    entrypoint: ["/usr/local/bin/ensure-db-password.sh"]' "$compose_file"

    # Add volume mount for the entrypoint script after the postgres_data volume line
    sed -i '/postgres_data:\/var\/lib\/postgresql\/data/a\      - ./db/ensure-db-password.sh:/usr/local/bin/ensure-db-password.sh:ro' "$compose_file"

    log "${GREEN}✓ docker-compose.yml patched with password sync entrypoint${NC}"
}

# Patch docker-compose.yml to add workbook/wiki shared volumes.
# Enables the backend to build the wiki (mkdocs) and share output with nginx.
patch_workbook_volumes() {
    local compose_file="$PLATFORM_DIR/docker-compose.yml"

    if [ ! -f "$compose_file" ]; then
        return 0
    fi

    # Skip if already patched
    if grep -q "workbook_data" "$compose_file" 2>/dev/null; then
        log "${GREEN}✓ docker-compose.yml already has workbook volumes${NC}"
        return 0
    fi

    log "Patching docker-compose.yml with workbook/wiki volumes..."

    if [ "$DRY_RUN" = true ]; then
        log "${YELLOW}[DRY RUN] Would patch docker-compose.yml with workbook volumes${NC}"
        return 0
    fi

    # Add workbook + wiki volumes to backend service (after the /labs:ro line)
    sed -i '/\${LABS_HOST_PATH}:\/labs:ro/a\      - workbook_data:/workbook\n      - wiki_html:/wiki_output' "$compose_file"

    # Add wiki volume to frontend service (before depends_on: backend)
    sed -i '/container_name: ocr-frontend/a\    volumes:\n      - wiki_html:/usr/share/nginx/wiki' "$compose_file"

    # Add named volumes at the end (after postgres_data:)
    sed -i '/postgres_data:/a\  workbook_data:\n  wiki_html:' "$compose_file"

    log "${GREEN}✓ docker-compose.yml patched with workbook/wiki volumes${NC}"
}

# Patch docker-compose.yml to add the wiki_courses shared volume.
# Enables per-course wiki builds (admin, winpt, linpt, etc.) shared between
# the backend builder and the nginx frontend.
patch_wiki_courses_volume() {
    local compose_file="$PLATFORM_DIR/docker-compose.yml"

    if [ ! -f "$compose_file" ]; then
        return 0
    fi

    # Skip if already patched
    if grep -q "wiki_courses" "$compose_file" 2>/dev/null; then
        log "${GREEN}✓ docker-compose.yml already has wiki_courses volume${NC}"
        return 0
    fi

    log "Patching docker-compose.yml with wiki_courses volume..."

    if [ "$DRY_RUN" = true ]; then
        log "${YELLOW}[DRY RUN] Would patch docker-compose.yml with wiki_courses volume${NC}"
        return 0
    fi

    # Add wiki_courses volume to backend service (after wiki_html line)
    sed -i '/wiki_html:\/wiki_output/a\      - wiki_courses:/wiki_courses' "$compose_file"

    # Add wiki_courses volume to frontend service (after wiki_html line)
    sed -i '/wiki_html:\/usr\/share\/nginx\/wiki$/a\      - wiki_courses:/usr/share/nginx/wiki-courses' "$compose_file"

    # Add named volume at the end (after wiki_html:)
    sed -i '/^  wiki_html:$/a\  wiki_courses:' "$compose_file"

    log "${GREEN}✓ docker-compose.yml patched with wiki_courses volume${NC}"
}

# Seed the workbook volume with source files and build all wikis.
# Copies Workbook/, mkdocs.yml, and all mkdocs-*.yml configs into the
# workbook_data volume, then triggers a full multi-wiki build.
seed_workbook() {
    log "${BLUE}Seeding workbook and building all wikis...${NC}"

    if [ "$DRY_RUN" = true ]; then
        log "${YELLOW}[DRY RUN] Would seed workbook and build all wikis${NC}"
        return 0
    fi

    cd "$PLATFORM_DIR"

    # Copy workbook source into the container's /workbook volume
    if [ -d "$REPO_DIR/Workbook" ] && [ -f "$REPO_DIR/mkdocs.yml" ]; then
        log "Copying workbook source files..."
        # Copy all mkdocs configs (main + course-specific)
        docker compose cp "$REPO_DIR/mkdocs.yml" backend:/workbook/mkdocs.yml 2>/dev/null || true
        for cfg in "$REPO_DIR"/mkdocs-*.yml; do
            [ -f "$cfg" ] || continue
            docker compose cp "$cfg" "backend:/workbook/$(basename "$cfg")" 2>/dev/null || true
        done
        # Use tar to copy directory contents into the volume
        tar -cf - -C "$REPO_DIR" Workbook | docker compose exec -T backend tar -xf - -C /workbook/ 2>/dev/null || true
        log "${GREEN}✓ Workbook source copied${NC}"
    else
        log "${YELLOW}⚠ Workbook/ or mkdocs.yml not found in repo — skipping seed${NC}"
        return 0
    fi

    # Build all wikis (default + admin + static configs + dynamic course wikis)
    log "Building all wikis (mkdocs build)..."
    if docker compose exec -T backend python -c "
from app.services.workbook_builder import build_all_wikis

# Gather dynamic course data from the database
courses = []
try:
    from app.database import SessionLocal
    from app.models import Course, CourseLabAssignment
    db = SessionLocal()
    try:
        for course in db.query(Course).filter(Course.wiki_slug.isnot(None)).all():
            assignments = db.query(CourseLabAssignment).filter(
                CourseLabAssignment.course_id == course.id,
            ).order_by(CourseLabAssignment.sort_order).all()
            paths = [a.lab.workbook for a in assignments if a.lab and a.lab.workbook]
            courses.append({
                'slug': course.wiki_slug,
                'name': course.name,
                'theme_color': course.wiki_theme_color or 'blue',
                'workbook_paths': paths,
            })
    finally:
        db.close()
except Exception as e:
    print(f'Warning: could not load courses from DB ({e}), building static configs only')

result = build_all_wikis(courses=courses if courses else None)
print(f\"Built {result['succeeded']} wikis OK, {result['failed']} failed in {result['total_duration_seconds']}s\")
for r in result['results']:
    status = 'OK' if r['success'] else 'FAIL'
    print(f\"  [{status}] {r['slug']} ({r['duration_seconds']}s)\")
    if not r['success']:
        print(f\"         {r['output'][:200]}\")
" 2>&1; then
        log "${GREEN}✓ All wikis built successfully${NC}"
    else
        log "${YELLOW}⚠ Wiki build had issues (some pages may still work)${NC}"
    fi
}

# Install/update the platform systemd service for auto-start on boot
install_systemd_service() {
    log "${BLUE}Installing/updating ocr-platform.service...${NC}"

    if [ "$DRY_RUN" = true ]; then
        log "${YELLOW}[DRY RUN] Would install ocr-platform.service${NC}"
        return 0
    fi

    cat > /etc/systemd/system/ocr-platform.service << SVCEOF
[Unit]
Description=OpenCyberRange Docker Compose Platform
Documentation=https://github.com/syntaxoverride/OpenCyberRange
After=docker.service docker.socket
Requires=docker.service
Before=ocr-vpn-firewall.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=${PLATFORM_DIR}

ExecStartPre=/bin/bash -c 'for i in \$(seq 1 30); do docker info >/dev/null 2>&1 && exit 0; sleep 1; done; echo "Docker daemon not ready after 30s" >&2; exit 1'
ExecStart=/usr/bin/docker compose --project-directory ${PLATFORM_DIR} up -d --wait
ExecStop=/usr/bin/docker compose --project-directory ${PLATFORM_DIR} down

TimeoutStartSec=120
TimeoutStopSec=60

[Install]
WantedBy=multi-user.target
SVCEOF

    systemctl daemon-reload
    systemctl enable ocr-platform.service 2>/dev/null || true
    log "${GREEN}✓ ocr-platform.service installed and enabled${NC}"
}

# Rebuild and restart containers
rebuild_containers() {
    log "${BLUE}Rebuilding and restarting containers...${NC}"
    
    if [ "$DRY_RUN" = true ]; then
        log "${YELLOW}[DRY RUN] Would run: docker compose build --no-cache backend frontend${NC}"
        log "${YELLOW}[DRY RUN] Would run: docker compose up -d${NC}"
        return 0
    fi
    
    cd "$PLATFORM_DIR"
    
    log "Building containers (this may take a while)..."
    if ! docker compose build --no-cache backend frontend; then
        error_exit "Docker build failed"
    fi
    
    log "Restarting services..."
    if ! docker compose up -d; then
        error_exit "Docker compose up failed"
    fi
    
    log "${GREEN}✓ Containers rebuilt and restarted${NC}"

    # Re-apply VPN firewall rules (Docker restart can clobber iptables)
    if systemctl is-enabled ocr-vpn-firewall.service &>/dev/null; then
        systemctl restart ocr-vpn-firewall.service 2>/dev/null && \
            log "${GREEN}✓ VPN firewall rules re-applied${NC}" || \
            log "${YELLOW}⚠ Could not restart VPN firewall service${NC}"
    fi
}

# Run database scripts (after containers are up)
run_database_scripts() {
    log "${BLUE}Running database scripts...${NC}"
    
    if [ "$DRY_RUN" = true ]; then
        log "${YELLOW}[DRY RUN] Would run database scripts${NC}"
        return 0
    fi
    
    cd "$PLATFORM_DIR"
    
    # Run seed script if needed (check if tracks table is empty)
    if [ -f "$PLATFORM_DIR/backend/app/scripts/seed_curriculum.py" ]; then
        log "Checking if seed data is needed..."
        # Run seed script inside container
        docker compose exec -T backend python /app/scripts/seed_curriculum.py 2>/dev/null || \
        docker compose exec -T backend python /app/app/scripts/seed_curriculum.py 2>/dev/null || \
        log "${YELLOW}Note: Seed script may have already been run${NC}"
    fi
    
    # Run lab discovery script to update labs and flags from lab.yaml files
    log "Discovering labs and updating flags..."
    
    # Verify scripts exist on host (deployed by rsync in apply_platform_update)
    if [ ! -f "$PLATFORM_DIR/backend/app/scripts/discover_labs.py" ]; then
        log "${YELLOW}Warning: discover_labs.py not found at $PLATFORM_DIR/backend/app/scripts/discover_labs.py${NC}"
        return 0
    fi
    
    # Try multiple possible script locations
    local script_found=false
    local script_output=""
    
    # Check what's actually in the container for debugging
    log "Checking container structure..."
    docker compose exec -T backend ls -la /app/app/ 2>&1 | head -10 || true
    docker compose exec -T backend test -d /app/app/scripts && docker compose exec -T backend ls -la /app/app/scripts/ 2>&1 || true
    
    # Check if script exists in container (backend is mounted at /app, so backend/app/scripts -> /app/app/scripts)
    if docker compose exec -T backend test -f /app/app/scripts/discover_labs.py 2>/dev/null; then
        log "Found script at /app/app/scripts/discover_labs.py"
        script_output=$(docker compose exec -T backend python /app/app/scripts/discover_labs.py 2>&1)
        script_found=true
    elif docker compose exec -T backend test -f /app/scripts/discover_labs.py 2>/dev/null; then
        log "Found script at /app/scripts/discover_labs.py"
        script_output=$(docker compose exec -T backend python /app/scripts/discover_labs.py 2>&1)
        script_found=true
    else
        # Try copying directly into running container as fallback
        log "Script not found in container, copying directly..."
        docker compose cp "$PLATFORM_DIR/backend/app/scripts/discover_labs.py" backend:/tmp/discover_labs.py 2>/dev/null
        if docker compose exec -T backend test -f /tmp/discover_labs.py 2>/dev/null; then
            script_output=$(docker compose exec -T backend python /tmp/discover_labs.py 2>&1)
            script_found=true
        fi
    fi
    
    if [ "$script_found" = true ]; then
        # Show output if there is any
        if [ -n "$script_output" ]; then
            echo "$script_output"
        fi
        log "${GREEN}✓ Lab discovery completed${NC}"
    else
        log "${YELLOW}Warning: discover_labs.py script not found in container${NC}"
        log "${YELLOW}  Host location: $PLATFORM_DIR/backend/app/scripts/discover_labs.py${NC}"
        log "${YELLOW}  Run manually: docker compose exec backend python /tmp/discover_labs.py${NC}"
        log "${YELLOW}  (after copying: docker compose cp $PLATFORM_DIR/backend/app/scripts/discover_labs.py backend:/tmp/)${NC}"
    fi

}

# Pre-build lab Docker images so student spawns are instant
prebuild_lab_images() {
    log "${BLUE}Pre-building lab Docker images...${NC}"

    if [ "$DRY_RUN" = true ]; then
        log "${YELLOW}[DRY RUN] Would run: prebuild-labs.sh${NC}"
        return 0
    fi

    local prebuild_script="$REPO_DIR/scripts/prebuild-labs.sh"
    if [ -f "$prebuild_script" ]; then
        chmod +x "$prebuild_script"
        # Run prebuild - don't fail deployment if some labs fail to build
        if bash "$prebuild_script"; then
            log "${GREEN}✓ All lab images pre-built successfully${NC}"
        else
            log "${YELLOW}⚠ Some lab images failed to build (see logs above)${NC}"
            log "${YELLOW}  Students may experience slower spawns for those labs${NC}"
        fi
    else
        log "${YELLOW}⚠ prebuild-labs.sh not found, skipping image pre-build${NC}"
    fi
}

# Verify deployment
verify_deployment() {
    log "${BLUE}Verifying deployment...${NC}"
    
    if [ "$DRY_RUN" = true ]; then
        log "${YELLOW}[DRY RUN] Would verify deployment${NC}"
        return 0
    fi
    
    cd "$PLATFORM_DIR"
    
    # Check if containers are running
    if ! docker compose ps | grep -q "Up"; then
        log "${YELLOW}Warning: Some containers may not be running${NC}"
    else
        log "${GREEN}✓ Containers are running${NC}"
    fi
    
    # Check health endpoint if available
    sleep 5  # Give containers time to start
    if curl -f http://localhost:8000/health &>/dev/null || curl -f http://localhost:8000/api/health &>/dev/null; then
        log "${GREEN}✓ Health check passed${NC}"
    else
        log "${YELLOW}Warning: Health check endpoint not responding (containers may still be starting)${NC}"
    fi
}

# Update state file
update_state() {
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    if [ "$DRY_RUN" = true ]; then
        return 0
    fi
    
    # Create directory if it doesn't exist and ensure proper permissions
    local state_dir=$(dirname "$STATE_FILE")
    if [ ! -d "$state_dir" ]; then
        mkdir -p "$state_dir" 2>/dev/null || {
            log "${YELLOW}Warning: Could not create state file directory${NC}"
            return 0
        }
    fi
    
    # Try to write state file, but don't fail if we can't
    if cat > "$STATE_FILE" << EOF 2>/dev/null; then
{
    "last_deployment": "$timestamp",
    "platform_applied": $DEPLOY_PLATFORM,
    "backup_path": "$BACKUP_DIR"
}
EOF
        log "${GREEN}✓ State file updated${NC}"
    else
        log "${YELLOW}Note: Could not write state file (permission issue)${NC}"
    fi
}

# Main execution
main() {
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
    echo -e "${BOLD}${MAGENTA}    ║${NC}${DIM}   Update Deployment                  ${MAGENTA}${BOLD}║${NC}"
    echo -e "${BOLD}${MAGENTA}    ╚═══════════════════════════════════════╝${NC}"
    echo ""
    log ""
    
    if [ "$DRY_RUN" = true ]; then
        log "${YELLOW}DRY RUN MODE - No changes will be made${NC}"
        log ""
    fi
    
    preflight_checks
    log ""
    
    local backup_path=$(create_backup)
    log ""
    
    git_pull
    log ""
    
    if [ "$DEPLOY_PLATFORM" = true ]; then
        apply_platform_update
        log ""
    fi

    if [ "$DEPLOY_PLATFORM" = true ]; then
        patch_docker_compose
        log ""
        patch_workbook_volumes
        log ""
        patch_wiki_courses_volume
        log ""
        rebuild_containers
        log ""
        run_database_scripts
        log ""
        seed_workbook
        log ""
        if [ "$PREBUILD_IMAGES" = true ]; then
            prebuild_lab_images
            log ""
        else
            log "${DIM}Skipping lab-image pre-build (labs build on first spawn). Pass --prebuild to build all now.${NC}"
            log ""
        fi
        verify_deployment
        log ""
        install_systemd_service
        log ""
    fi

    update_state
    
    log "${GREEN}========================================${NC}"
    log "${GREEN}Deployment completed successfully!${NC}"
    log "${GREEN}========================================${NC}"
    log ""
    log "Backup location: $backup_path"
    log "Log file: $LOG_FILE"
    log "State file: $STATE_FILE"
}

# Run main function
main "$@"

