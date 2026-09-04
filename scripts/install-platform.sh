#!/bin/bash
# ==============================================================================
# OpenCyberRange — Platform Installer
# ==============================================================================
#
# Installs or updates the Docker-based platform (backend, frontend, database).
# Typically called from setup-range-server.sh, but can also run standalone.
#
# USAGE:
#   bash install-platform.sh              # Interactive menu
#   bash install-platform.sh --fresh      # Non-interactive fresh install
#   bash install-platform.sh --update     # Non-interactive update
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
# Detect actual user's home directory even when running as root
if [ -n "${SUDO_USER:-}" ]; then
    # Ran via: sudo bash install-platform.sh
    ACTUAL_HOME=$(getent passwd "$SUDO_USER" | cut -d: -f6)
elif [ "$(id -u)" -eq 0 ] && [ -n "${OCR_PLATFORM_DIR:-}" ]; then
    # Running as root, but the caller pinned the runtime dir explicitly
    # (setup-range-server.sh always exports OCR_PLATFORM_DIR). No home to
    # guess, so proceed — this is the supported root-only / cloud-VM path.
    ACTUAL_HOME="$HOME"
elif [ "$(id -u)" -eq 0 ]; then
    # Running as root (sudo su / su - root) with no pinned dir — refuse to
    # guess a home, tell the user how to run it.
    echo "ERROR: Do not run this script as root directly." >&2
    echo "       Use:  sudo bash $0 [--fresh|--update]" >&2
    echo "       (sudo preserves your real username so the platform" >&2
    echo "        installs to your home directory, not /root)" >&2
    echo "       To install as root on a root-only host, set the target dir:" >&2
    echo "         OCR_PLATFORM_DIR=/opt/opencyberrange bash $0 --fresh" >&2
    exit 1
else
    ACTUAL_HOME="$HOME"
fi
# Runtime platform directory. Defaults to a headless-friendly path under the
# user's home (NOT ~/Desktop, which does not exist on servers/cloud VMs).
# Override with OCR_PLATFORM_DIR. setup-range-server.sh exports this so both
# scripts agree.
PLATFORM_DIR="${OCR_PLATFORM_DIR:-$ACTUAL_HOME/opencyberrange}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="$REPO_DIR/scripts/install.log"

# Installation mode
FRESH_INSTALL=false
UPDATE_PLATFORM=false
UPDATE_ALL=false

# ── Parse CLI arguments ──────────────────────────────────────────────────────
CLI_MODE=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --fresh)  CLI_MODE="fresh"; shift ;;
        --update) CLI_MODE="update"; shift ;;
        --help|-h)
            echo "Usage: bash $0 [--fresh|--update|--help]"
            echo ""
            echo "  --fresh     Non-interactive fresh install"
            echo "  --update    Non-interactive platform update"
            echo "  --help      Show this help"
            echo "  (no args)   Interactive menu"
            exit 0
            ;;
        *) echo "Unknown option: $1. Use --help for usage."; exit 1 ;;
    esac
done

# Logging function
log() {
    echo -e "$1" | tee -a "$LOG_FILE"
}

# Error handling
error_exit() {
    log "${RED}ERROR: $1${NC}"
    exit 1
}

# Check if installation exists
check_existing_installation() {
    if [ -d "$PLATFORM_DIR" ] && [ -f "$PLATFORM_DIR/docker-compose.yml" ]; then
        return 0
    else
        return 1
    fi
}

# Display menu and get user choice
show_menu() {
    local has_existing=false
    if check_existing_installation; then
        has_existing=true
    fi

    log ""
    log "  Repository: $REPO_DIR"
    log "  Platform:   $PLATFORM_DIR"
    log ""

    if [ "$has_existing" = true ]; then
        log "${GREEN}  Existing installation detected.${NC}"
        log ""
        log "    ${CYAN}1)${NC} Update Platform"
        log "    ${CYAN}2)${NC} Fresh Install ${YELLOW}(overwrites existing)${NC}"
        log "    ${CYAN}3)${NC} Exit"
        log ""
        read -rp "  Select [1-3]: " choice || choice="3"

        case $choice in
            1)
                UPDATE_PLATFORM=true
                UPDATE_ALL=true
                ;;
            2)
                log "${YELLOW}WARNING: This will overwrite your existing installation!${NC}"
                read -rp "  Are you sure? Type 'yes' to continue: " confirm
                if [ "$confirm" = "yes" ]; then
                    FRESH_INSTALL=true
                else
                    log "${BLUE}Cancelled — returning to menu.${NC}"
                    show_menu
                fi
                ;;
            3)
                log "${BLUE}Exiting.${NC}"
                exit 0
                ;;
            *)
                log "${YELLOW}Invalid choice — enter 1, 2, or 3${NC}"
                log ""
                show_menu
                ;;
        esac
    else
        log "${BLUE}  No existing installation detected.${NC}"
        log ""
        log "    ${CYAN}1)${NC} Fresh Install"
        log "    ${CYAN}2)${NC} Exit"
        log ""
        read -rp "  Select [1-2]: " choice || choice="2"

        case $choice in
            1)
                FRESH_INSTALL=true
                UPDATE_ALL=true
                ;;
            2)
                log "${BLUE}Exiting.${NC}"
                exit 0
                ;;
            *)
                log "${YELLOW}Invalid choice — enter 1 or 2${NC}"
                log ""
                show_menu
                ;;
        esac
    fi
}

# Pre-flight checks — installs missing dependencies automatically
preflight_checks() {
    log "${BLUE}Running pre-flight checks...${NC}"

    # Check if git repo (optional - ZIP downloads work for both installs and updates)
    if [ ! -d "$REPO_DIR/.git" ]; then
        if [ "$UPDATE_MODE" = true ]; then
            log "${YELLOW}⚠ Not a git repository - assuming ZIP download${NC}"
            log "${YELLOW}  Make sure you've extracted the latest ZIP before running updates${NC}"
        else
            log "${YELLOW}⚠ Not a git repository (this is OK for ZIP downloads)${NC}"
            log "${YELLOW}  For future updates, you can either:${NC}"
            log "${YELLOW}    1. Download a new ZIP and extract it, then run this script again${NC}"
            log "${YELLOW}    2. Clone the repository: git clone https://github.com/syntaxoverride/OpenCyberRange.git${NC}"
        fi
    fi

    # Install Docker if missing
    if ! command -v docker &> /dev/null; then
        log "${YELLOW}Docker not found — installing...${NC}"
        sudo apt-get update -qq
        sudo apt-get install -y docker.io
        sudo systemctl enable --now docker
        sudo usermod -aG docker "$USER"
        log "${GREEN}✓ Docker installed${NC}"
    else
        log "${GREEN}✓ Docker installed ($(docker --version))${NC}"
    fi

    # Install Docker Compose if missing
    if ! docker compose version &> /dev/null; then
        log "${YELLOW}Docker Compose not found — installing...${NC}"
        sudo apt-get update -qq
        sudo apt-get install -y docker-compose-plugin 2>/dev/null || \
            sudo apt-get install -y docker-compose-v2 2>/dev/null || \
            error_exit "Could not install Docker Compose v2. Please install it manually."
        log "${GREEN}✓ Docker Compose installed${NC}"
    else
        log "${GREEN}✓ Docker Compose available${NC}"
    fi

    # Check if user can run docker
    if ! docker ps &> /dev/null; then
        error_exit "Cannot access Docker. You may need to:\n  sudo usermod -aG docker $USER\n  (then log out and back in)"
    fi

    log "${GREEN}✓ Pre-flight checks passed${NC}"
}

# Generate secure random string
generate_secret() {
    openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | base64 | tr -d '\n'
}

# Generate Fernet encryption key for WireGuard
generate_fernet_key() {
    # Try Python3 with cryptography library
    if command -v python3 &> /dev/null; then
        python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || \
        python3 -c "import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())" 2>/dev/null || \
        generate_secret
    else
        # Fallback to random hex if Python not available
        generate_secret
    fi
}

# Detect or prompt for WireGuard configuration
# When called from setup-range-server.sh, OCR_WG_* env vars are pre-set
# and we skip interactive prompts entirely.
prompt_wireguard_config() {
    log ""
    log "${CYAN}=== WireGuard Configuration ===${NC}"
    log ""

    # VPN is always enabled — detect keys and endpoint for both local and internet modes

    # ── 1. Server public key ────────────────────────────────────────────────
    local detected_pubkey="${OCR_WG_SERVER_PUBKEY:-}"
    if [ -z "$detected_pubkey" ] && [ -f "/etc/wireguard/server_public.key" ]; then
        detected_pubkey=$(cat /etc/wireguard/server_public.key 2>/dev/null)
    fi
    if [ -z "$detected_pubkey" ] && command -v wg &> /dev/null; then
        detected_pubkey=$(sudo wg show wg0 public-key 2>/dev/null || echo "")
    fi

    # ── 2. Server endpoint (public IP + port) ───────────────────────────────
    local detected_endpoint="${OCR_WG_SERVER_ENDPOINT:-}"
    if [ -z "$detected_endpoint" ]; then
        local detected_ip=""
        detected_ip=$(curl -4 -s --connect-timeout 5 ifconfig.me 2>/dev/null || \
                      curl -4 -s --connect-timeout 5 icanhazip.com 2>/dev/null || \
                      curl -4 -s --connect-timeout 5 api.ipify.org 2>/dev/null || \
                      echo "")
        if [ -n "$detected_ip" ]; then
            detected_endpoint="${detected_ip}:51820"
        fi
    fi

    # ── 3. Peer Manager API key ─────────────────────────────────────────────
    local detected_api_key="${OCR_WG_API_KEY:-}"
    if [ -z "$detected_api_key" ] && [ -f "/opt/ocr-peer-manager/peer_manager.env" ]; then
        detected_api_key=$(grep -oP 'PEER_MANAGER_API_KEY=\K.*' /opt/ocr-peer-manager/peer_manager.env 2>/dev/null || echo "")
    fi

    # ── 4. Peer Manager API URL ─────────────────────────────────────────────
    local detected_api_url="${OCR_WG_API_URL:-}"

    # ── If all critical values were detected, skip prompts ──────────────────
    if [ -n "$detected_pubkey" ] && [ -n "$detected_endpoint" ]; then
        log "${GREEN}✓ WireGuard public key : ${detected_pubkey}${NC}"
        log "${GREEN}✓ Server endpoint      : ${detected_endpoint}${NC}"
        [ -n "$detected_api_key" ] && log "${GREEN}✓ Peer Manager API key : (detected)${NC}"
        [ -n "$detected_api_url" ] && log "${GREEN}✓ Peer Manager API URL : ${detected_api_url}${NC}"

        WG_PUBLIC_KEY="$detected_pubkey"
        WG_ENDPOINT="$detected_endpoint"
        WG_API_KEY="${detected_api_key:-}"
        WG_API_URL="${detected_api_url:-http://host.docker.internal:5000}"
        WG_NETWORK_BASE="10.100"
        WG_CLIENT_BASE="10.0.0"

        # Server public hostname (skippable via SERVER_PUBLIC_HOST env var)
        if [ -z "${SERVER_PUBLIC_HOST:-}" ]; then
            # Try to default to the detected public IP
            local default_host="${detected_endpoint%%:*}"
            default_host="${default_host:-localhost}"
            log ""
            log "${CYAN}What hostname or IP will students use to access this server?${NC}"
            log "${DIM}  Examples: lab.yourdomain.com, 203.0.113.45, or localhost (for testing)${NC}"
            read -p "  Server hostname [${default_host}]: " SERVER_PUBLIC_HOST
            SERVER_PUBLIC_HOST=${SERVER_PUBLIC_HOST:-"$default_host"}
        else
            log "${GREEN}✓ Server hostname      : ${SERVER_PUBLIC_HOST}${NC}"
        fi
        return
    fi

    # ── Interactive fallback — prompt for anything we couldn't detect ───────
    log ""
    if [ -n "$detected_pubkey" ]; then
        log "${GREEN}✓ Auto-detected WireGuard public key${NC}"
    fi
    if [ -n "$detected_endpoint" ]; then
        log "${GREEN}✓ Auto-detected server endpoint: ${detected_endpoint}${NC}"
    fi
    if [ -n "$detected_api_key" ]; then
        log "${GREEN}✓ Auto-detected Peer Manager API key${NC}"
    fi
    log ""

    if [ -n "$detected_endpoint" ]; then
        read -p "WireGuard Server Endpoint [${detected_endpoint}]: " WG_ENDPOINT
        WG_ENDPOINT=${WG_ENDPOINT:-"$detected_endpoint"}
    else
        log "${YELLOW}Could not auto-detect this server's public IP address.${NC}"
        log "${DIM}  This is your server's public IP + WireGuard port (e.g. 203.0.113.45:51820)${NC}"
        log "${DIM}  Find it with: curl -4 ifconfig.me${NC}"
        read -p "WireGuard Server Endpoint (IP:51820): " WG_ENDPOINT
    fi

    if [ -n "$detected_pubkey" ]; then
        read -p "WireGuard Server Public Key [${detected_pubkey}]: " WG_PUBLIC_KEY
        WG_PUBLIC_KEY=${WG_PUBLIC_KEY:-"$detected_pubkey"}
    else
        log "${DIM}  Find it with: sudo cat /etc/wireguard/server_public.key${NC}"
        read -p "WireGuard Server Public Key: " WG_PUBLIC_KEY
    fi

    # Peer Manager API URL — internal, no need to prompt
    WG_API_URL="${detected_api_url:-http://host.docker.internal:5000}"

    if [ -n "$detected_api_key" ]; then
        log "${GREEN}✓ Auto-detected Peer Manager API key${NC}"
        WG_API_KEY="$detected_api_key"
    else
        log "${YELLOW}Could not auto-detect Peer Manager API key.${NC}"
        log "${YELLOW}If WireGuard was set up by setup-range-server.sh, this key is at:${NC}"
        log "${YELLOW}  /opt/ocr-peer-manager/peer_manager.env${NC}"
        log ""
        read -p "Peer Manager API Key: " WG_API_KEY
    fi

    # Network settings — use safe defaults (no prompt needed)
    WG_NETWORK_BASE="10.100"
    WG_CLIENT_BASE="10.0.0"

    # Server hostname — default to IP from endpoint if available
    local default_host="${WG_ENDPOINT%%:*}"
    default_host="${default_host:-localhost}"
    log ""
    log "${CYAN}What hostname or IP will students use to access this server?${NC}"
    log "${DIM}  Examples: lab.yourdomain.com, 203.0.113.45, or localhost (for testing)${NC}"
    read -p "  Server hostname [${default_host}]: " SERVER_PUBLIC_HOST
    SERVER_PUBLIC_HOST=${SERVER_PUBLIC_HOST:-"$default_host"}

    # Validate and auto-correct swapped values
    # WireGuard public keys are 44-char base64 strings (ending in =)
    # Endpoints are IP:port (e.g. 10.0.0.1:51820)
    _looks_like_wg_key() { [[ "$1" =~ ^[A-Za-z0-9+/]{42,43}=$ ]]; }
    _looks_like_endpoint() { [[ "$1" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+:[0-9]+$ ]]; }

    if _looks_like_wg_key "$WG_ENDPOINT" && _looks_like_endpoint "$WG_PUBLIC_KEY"; then
        log "${YELLOW}⚠ Endpoint and public key appear swapped — correcting${NC}"
        local tmp="$WG_ENDPOINT"
        WG_ENDPOINT="$WG_PUBLIC_KEY"
        WG_PUBLIC_KEY="$tmp"
    fi

    if [ -n "$WG_ENDPOINT" ] && ! _looks_like_endpoint "$WG_ENDPOINT"; then
        log "${RED}⚠ WARNING: Server endpoint doesn't look like IP:port — got: ${WG_ENDPOINT}${NC}"
        log "${RED}  Expected format: 203.0.113.45:51820${NC}"
        log "${RED}  You can fix this later in: $PLATFORM_DIR/.env (WG_SERVER_ENDPOINT)${NC}"
    fi
    if [ -n "$WG_PUBLIC_KEY" ] && ! _looks_like_wg_key "$WG_PUBLIC_KEY"; then
        log "${RED}⚠ WARNING: Public key doesn't look like a WireGuard key — got: ${WG_PUBLIC_KEY}${NC}"
        log "${RED}  WireGuard keys are 44-character base64 strings ending in =${NC}"
        log "${RED}  You can fix this later in: $PLATFORM_DIR/.env (WG_SERVER_PUBLIC_KEY)${NC}"
    fi
    if [ -z "$WG_ENDPOINT" ]; then
        log "${RED}⚠ WARNING: WireGuard Server Endpoint is empty!${NC}"
        log "${RED}  Students won't be able to download VPN configs until this is set.${NC}"
        log "${RED}  Fix: Edit $PLATFORM_DIR/.env and set WG_SERVER_ENDPOINT=YOUR_IP:51820${NC}"
        log "${RED}  Then restart: docker compose -f $PLATFORM_DIR/docker-compose.yml restart backend${NC}"
    fi
    if [ -z "$WG_PUBLIC_KEY" ]; then
        log "${RED}⚠ WARNING: WireGuard Server Public Key is empty!${NC}"
        log "${RED}  Students won't be able to download VPN configs until this is set.${NC}"
        log "${RED}  Fix: Edit $PLATFORM_DIR/.env and set WG_SERVER_PUBLIC_KEY=<your key>${NC}"
        log "${RED}  Find it: sudo cat /etc/wireguard/server_public.key${NC}"
    fi
}

# Create .env file for fresh install
create_env_file() {
    log "${BLUE}Creating .env file...${NC}"
    
    # Generate JWT secret
    JWT_SECRET=$(generate_secret)

    # Generate database password
    DB_PASSWORD=$(openssl rand -base64 18 | tr -d '/+=' | head -c 24)

    # Generate WireGuard encryption key
    log "Generating WireGuard encryption key..."
    WG_ENCRYPTION_KEY=$(generate_fernet_key)

    # Generate the first-run setup token. The /setup wizard creates the very
    # first administrator, and the backend only enforces its token check when
    # SETUP_TOKEN is set. Leaving it empty means whoever reaches the server
    # between "compose up" and the operator opening a browser can claim the
    # admin account, which is survivable on an isolated lab box and is not on
    # an internet-facing one. Generate it always; the installer prints it.
    SETUP_TOKEN=$(generate_secret)
    
    # Prompt for WireGuard config
    prompt_wireguard_config
    
    # Determine labs path. Lab definitions live under platform/labs in the repo.
    if [ -d "$REPO_DIR/platform/labs" ]; then
        LABS_PATH="$REPO_DIR/platform/labs"
    else
        LABS_PATH="$PLATFORM_DIR/labs"
    fi
    
    # Create .env file
    cat > "$PLATFORM_DIR/.env" << EOF
# OpenCyberRange Platform Configuration
# Generated on $(date)

# JWT Secret - CHANGE THIS IN PRODUCTION
JWT_SECRET=$JWT_SECRET

# First-run setup token. Required by the /setup wizard to create the first
# administrator. Safe to delete once that account exists.
SETUP_TOKEN=$SETUP_TOKEN

# WireGuard Configuration
WG_SERVER_ENDPOINT=$WG_ENDPOINT
WG_SERVER_PUBLIC_KEY=$WG_PUBLIC_KEY

# Peer Manager API (for VPN peer management)
WG_API_URL=$WG_API_URL
WG_API_KEY=$WG_API_KEY

# WireGuard Key Encryption (auto-generated)
WG_ENCRYPTION_KEY=$WG_ENCRYPTION_KEY

# Network Configuration  
WG_NETWORK_BASE=$WG_NETWORK_BASE
WG_CLIENT_BASE=$WG_CLIENT_BASE

# Host path for lab builds
LABS_HOST_PATH=$LABS_PATH

# Server hostname (for VPN config generation and URLs)
SERVER_PUBLIC_HOST=${SERVER_PUBLIC_HOST:-localhost}

# CORS — allowed frontend origins
CORS_ORIGINS=http://localhost,https://localhost

# JWT defaults
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Database
DATABASE_URL=postgresql://labuser:${DB_PASSWORD}@db:5432/labdb
POSTGRES_USER=labuser
POSTGRES_PASSWORD=${DB_PASSWORD}
POSTGRES_DB=labdb

# Deployment mode (local or internet)
DEPLOYMENT_MODE=${OCR_DEPLOYMENT_MODE:-internet}
EOF
    
    log "${GREEN}✓ .env file created (all secrets auto-generated)${NC}"
}

# Create docker-compose.yml for platform
create_docker_compose() {
    log "${BLUE}Creating docker-compose.yml...${NC}"
    
    cat > "$PLATFORM_DIR/docker-compose.yml" << 'EOF'
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    container_name: ocr-db
    entrypoint: ["/usr/local/bin/ensure-db-password.sh"]
    # Overriding entrypoint clears the image CMD, so the server argument
    # must come back explicitly or docker-entrypoint.sh starts nothing
    # and the container exits before a single log line.
    command: ["postgres"]
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-labuser}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-labpass}
      POSTGRES_DB: ${POSTGRES_DB:-labdb}
      TZ: UTC
      PGTZ: UTC
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./db/ensure-db-password.sh:/usr/local/bin/ensure-db-password.sh:ro
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-labuser}"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: ocr-backend
    ports:
      - "127.0.0.1:8000:8000"
    extra_hosts:
      - "host.docker.internal:host-gateway"
    environment:
      DATABASE_URL: ${DATABASE_URL:-postgresql://labuser:labpass@db:5432/labdb}
      JWT_SECRET: ${JWT_SECRET}
      SETUP_TOKEN: ${SETUP_TOKEN:-}
      JWT_ALGORITHM: ${JWT_ALGORITHM:-HS256}
      JWT_EXPIRATION_HOURS: ${JWT_EXPIRATION_HOURS:-24}
      WG_SERVER_ENDPOINT: ${WG_SERVER_ENDPOINT}
      WG_SERVER_PUBLIC_KEY: ${WG_SERVER_PUBLIC_KEY}
      WG_API_URL: ${WG_API_URL}
      WG_API_KEY: ${WG_API_KEY}
      WG_ENCRYPTION_KEY: ${WG_ENCRYPTION_KEY}
      WG_NETWORK_BASE: ${WG_NETWORK_BASE:-10.100}
      WG_CLIENT_BASE: ${WG_CLIENT_BASE:-10.0.0}
      LABS_HOST_PATH: ${LABS_HOST_PATH}
      SERVER_PUBLIC_HOST: ${SERVER_PUBLIC_HOST:-localhost}
      CORS_ORIGINS: ${CORS_ORIGINS:-http://localhost,https://localhost}
      TZ: UTC
    volumes:
      - ./backend:/app
      - /var/run/docker.sock:/var/run/docker.sock
      - ${LABS_HOST_PATH}:/labs:ro
      - workbook_data:/workbook
      # Exercise Studio template catalog lives outside the backend build
      # context, so it is mounted in read-only. (The Studio publish-gate
      # linters are baked into the backend image, not mounted.)
      - ./templates:/app/templates:ro
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: ocr-frontend
    ports:
      - "80:80"
      - "443:443"
    volumes:
      # The wiki is baked into the image (prebuilt track tree). Do NOT mount a
      # named volume here -- an empty wiki_html volume would shadow the baked
      # content and every workbook link would 404.
      # Self-signed TLS: the entrypoint enables HTTPS when these files exist.
      - ./certs:/etc/nginx/certs:ro
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  postgres_data:
  workbook_data:
EOF
    
    log "${GREEN}✓ docker-compose.yml created${NC}"
}

# Create directory structure
create_directory_structure() {
    log "${BLUE}Creating directory structure...${NC}"
    
    mkdir -p "$PLATFORM_DIR/backend/app"
    mkdir -p "$PLATFORM_DIR/frontend/src"
    mkdir -p "$PLATFORM_DIR/labs"
    mkdir -p "$PLATFORM_DIR/.backups"
    
    log "${GREEN}✓ Directory structure created${NC}"
}

# Copy platform files
copy_platform_files() {
    log "${BLUE}Copying platform files...${NC}"
    
    # Copy backend
    if [ -d "$REPO_DIR/platform/backend" ]; then
        log "Copying backend files..."
        cp -r "$REPO_DIR/platform/backend/"* "$PLATFORM_DIR/backend/" 2>/dev/null || true
    else
        error_exit "Platform backend directory not found"
    fi
    
    # Copy frontend
    if [ -d "$REPO_DIR/platform/frontend" ]; then
        log "Copying frontend files..."
        cp -r "$REPO_DIR/platform/frontend/"* "$PLATFORM_DIR/frontend/" 2>/dev/null || true
    else
        error_exit "Platform frontend directory not found"
    fi

    # Copy db files (ensure-db-password entrypoint wrapper)
    if [ -d "$REPO_DIR/platform/db" ]; then
        log "Copying db files..."
        mkdir -p "$PLATFORM_DIR/db"
        cp -r "$REPO_DIR/platform/db/"* "$PLATFORM_DIR/db/" 2>/dev/null || true
        chmod +x "$PLATFORM_DIR/db/"*.sh 2>/dev/null || true
    fi

    # Copy the Exercise Studio template catalog (legitimate app data) next to the
    # compose file so the backend can mount it. The publish-gate linters are
    # baked into the backend image (app/services/workbook_linters), not copied.
    if [ -d "$REPO_DIR/platform/templates" ]; then
        log "Copying Exercise Studio templates..."
        mkdir -p "$PLATFORM_DIR/templates"
        cp -r "$REPO_DIR/platform/templates/"* "$PLATFORM_DIR/templates/" 2>/dev/null || true
    fi

    # Copy labs (symlink or copy). Lab definitions live under platform/labs.
    if [ -d "$REPO_DIR/platform/labs" ]; then
        log "Setting up labs directory..."
        if [ "$REPO_DIR/platform/labs" = "$PLATFORM_DIR/labs" ]; then
            log "Labs already in place (same directory)"
        elif [ ! -L "$PLATFORM_DIR/labs" ] && [ ! -d "$PLATFORM_DIR/labs/Windows" ]; then
            # Remove the empty labs directory created by mkdir so we can symlink properly
            rmdir "$PLATFORM_DIR/labs" 2>/dev/null || true
            # Try symlink first, fall back to copy
            ln -sf "$REPO_DIR/platform/labs" "$PLATFORM_DIR/labs" 2>/dev/null || {
                mkdir -p "$PLATFORM_DIR/labs"
                cp -r "$REPO_DIR/platform/labs/"* "$PLATFORM_DIR/labs/" 2>/dev/null || true
            }
        fi
    fi
    
    log "${GREEN}✓ Platform files copied${NC}"
}

# Copy VPN update files (deprecated - VPN is now integrated into main platform)
copy_vpn_files() {
    log "${GREEN}VPN features are now integrated into the main platform.${NC}"
    log "${GREEN}✓ VPN files included in platform (no separate copy needed)${NC}"
}

# Run database migrations
run_migrations() {
    log "${BLUE}Running database migrations...${NC}"
    
    cd "$PLATFORM_DIR"
    
    # Wait for database to be ready
    log "Waiting for database to be ready..."
    sleep 5
    
    # Initialize database schema (idempotent - safe to run multiple times)
    if [ -f "$REPO_DIR/platform/scripts/init_database.sh" ]; then
        log "Initializing database schema..."
        chmod +x "$REPO_DIR/platform/scripts/init_database.sh"
        bash "$REPO_DIR/platform/scripts/init_database.sh" || log "${YELLOW}Warning: Database initialization may have issues${NC}"
    fi
    
    # VPN schema is now included in the main database initialization
    # No separate VPN migration needed
    
    log "${GREEN}✓ Migrations completed${NC}"
}

# Seed database
seed_database() {
    log "${BLUE}Seeding database with curriculum data...${NC}"
    
    cd "$PLATFORM_DIR"
    
    # Copy seed script
    if [ -f "$REPO_DIR/platform/scripts/seed_curriculum.py" ]; then
        mkdir -p "$PLATFORM_DIR/backend/app/scripts"
        cp "$REPO_DIR/platform/scripts/seed_curriculum.py" "$PLATFORM_DIR/backend/app/scripts/" 2>/dev/null || true
        
        # Wait for backend to be ready
        log "Waiting for backend container to be ready..."
        sleep 10
        
        # Run seed script
        docker compose exec -T backend python /app/scripts/seed_curriculum.py 2>/dev/null || \
        docker compose exec -T backend python /app/app/scripts/seed_curriculum.py 2>/dev/null || \
        log "${YELLOW}Note: Seed script may have already been run${NC}"
    fi
    
    log "${GREEN}✓ Database seeding completed${NC}"
}


# skip cleanly. The core Docker-only curriculum is unaffected either way.

# Build and start containers
build_and_start() {
    log "${BLUE}Building and starting containers...${NC}"
    log "${YELLOW}This may take several minutes...${NC}"
    
    cd "$PLATFORM_DIR"
    
    # Build containers
    log "Building containers..."
    docker compose build --no-cache || error_exit "Docker build failed"
    
    # Start containers
    log "Starting containers..."
    docker compose up -d || error_exit "Docker compose up failed"

    # Build RangeBox images (browser-based desktops). RangeBox/ and UbuntuBox/
    # sit at the repo root next to platform/, so resolve them from REPO_DIR --
    # PLATFORM_DIR/../RangeBox pointed at ~/RangeBox in the documented layout and
    # the build was skipped silently, leaving students a dead "Launch RangeBox".
    if [ -d "$REPO_DIR/RangeBox" ]; then
        log "Building RangeBox image (Kali desktop)..."
        if docker build -t opencyberrange/rangebox:lite --target lite "$REPO_DIR/RangeBox/"; then
            log "${GREEN}✓ RangeBox image built${NC}"
        else
            warn "RangeBox build FAILED — the in-browser attack desktop will not start. Students without a VPN cannot reach labs until this is rebuilt."
        fi
    else
        warn "RangeBox/ not found at $REPO_DIR — skipping the in-browser desktop build."
    fi
    if [ -d "$REPO_DIR/UbuntuBox" ]; then
        log "Building UbuntuBox image (Ubuntu desktop)..."
        docker build -t opencyberrange/ubuntubox:latest "$REPO_DIR/UbuntuBox/" || \
            warn "UbuntuBox build failed — this is optional"
    fi

    log "${GREEN}✓ Containers built and started${NC}"
}

# Verify installation
verify_installation() {
    log "${BLUE}Verifying installation...${NC}"
    
    cd "$PLATFORM_DIR"
    
    # Wait for services to start
    sleep 10
    
    # Check containers
    if docker compose ps | grep -q "Up"; then
        log "${GREEN}✓ Containers are running${NC}"
    else
        log "${YELLOW}Warning: Some containers may not be running${NC}"
        docker compose ps
    fi
    
    # Check health endpoint
    if curl -f http://localhost:8000/health &>/dev/null || curl -f http://localhost:8000/api/health &>/dev/null; then
        log "${GREEN}✓ Backend health check passed${NC}"
    else
        log "${YELLOW}Warning: Backend health check failed (may still be starting)${NC}"
    fi
    
    # Check frontend
    if curl -f http://localhost/ &>/dev/null || curl -f http://localhost:80/ &>/dev/null; then
        log "${GREEN}✓ Frontend is accessible${NC}"
    else
        log "${YELLOW}Warning: Frontend may not be accessible yet${NC}"
    fi
}

# Install and enable the platform systemd service for auto-start on boot
install_systemd_service() {
    log "${BLUE}Installing ocr-platform.service for auto-start on boot...${NC}"

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
    systemctl enable ocr-platform.service
    log "${GREEN}✓ ocr-platform.service installed and enabled — platform will auto-start on boot${NC}"
}

# Remove existing installation (for fresh install)
cleanup_old_installation() {
    # Safety: never delete the repo directory we're running from
    if [ "$PLATFORM_DIR" = "$REPO_DIR" ]; then
        log "${YELLOW}Platform directory is the same as repository directory — skipping cleanup${NC}"
        # Still stop containers if running
        if [ -f "$PLATFORM_DIR/docker-compose.yml" ]; then
            cd "$PLATFORM_DIR"
            docker compose down -v 2>/dev/null || true
        fi
        return
    fi

    if [ -d "$PLATFORM_DIR" ]; then
        log "${YELLOW}Removing existing installation at $PLATFORM_DIR...${NC}"

        # Stop and remove containers if running
        if [ -f "$PLATFORM_DIR/docker-compose.yml" ]; then
            cd "$PLATFORM_DIR"
            docker compose down -v 2>/dev/null || true
        fi

        # Remove directory
        rm -rf "$PLATFORM_DIR"
        log "${GREEN}✓ Old installation removed${NC}"
    fi
}

# Admin account bootstrap happens in the browser via the /setup wizard.
# The wizard (backend routers/setup.py) creates the first admin only when no
# users exist, under a Postgres advisory lock, and seeds default settings.
# No credentials are pre-created by this installer.

# Migrate WireGuard keys (encrypt existing keys if any)
migrate_wireguard_keys() {
    log "${BLUE}Running WireGuard key encryption migration...${NC}"
    
    cd "$PLATFORM_DIR"
    
    # Check if migration script exists
    if [ ! -f "$REPO_DIR/platform/scripts/migrate_wg_keys.py" ]; then
        log "${YELLOW}Note: Migration script not found, skipping${NC}"
        return 0
    fi
    
    # Copy migration script to backend (same pattern as seed_curriculum)
    if [ -f "$REPO_DIR/platform/scripts/migrate_wg_keys.py" ]; then
        mkdir -p "$PLATFORM_DIR/backend/app/scripts" 2>/dev/null || true
        cp "$REPO_DIR/platform/scripts/migrate_wg_keys.py" "$PLATFORM_DIR/backend/app/scripts/" 2>/dev/null || true
        
        # Wait for backend to be ready
        log "${YELLOW}Waiting for backend to be ready...${NC}"
        for i in {1..30}; do
            if docker compose exec -T backend python3 -c "import sys; sys.exit(0)" > /dev/null 2>&1; then
                break
            fi
            if [ $i -eq 30 ]; then
                log "${YELLOW}Warning: Backend not ready, skipping key migration${NC}"
                return 0
            fi
            sleep 1
        done
        
        # Run migration script (safe for fresh installs - will find 0 keys and complete successfully)
        log "Running key encryption migration..."
        if docker compose exec -T backend python3 /app/scripts/migrate_wg_keys.py 2>/dev/null || \
           docker compose exec -T backend python3 /app/app/scripts/migrate_wg_keys.py 2>/dev/null; then
            log "${GREEN}✓ WireGuard key migration completed${NC}"
        else
            log "${YELLOW}Note: Key migration completed (no existing keys to migrate on fresh install)${NC}"
        fi
    else
        log "${YELLOW}Note: Migration script not found, skipping${NC}"
    fi
}

# Fresh installation workflow
fresh_install() {
    log "${CYAN}========================================${NC}"
    log "${CYAN}Fresh Installation Mode${NC}"
    log "${CYAN}========================================${NC}"
    log ""
    
    # Remove existing installation if present
    cleanup_old_installation
    log ""
    
    create_directory_structure
    log ""
    
    create_env_file
    log ""
    
    create_docker_compose
    log ""
    
    copy_platform_files
    log ""
    
    copy_vpn_files
    log ""
    
    build_and_start
    log ""
    
    run_migrations
    log ""
    
    seed_database
    log ""
    
    migrate_wireguard_keys
    log ""
    
    verify_installation
    log ""

    install_systemd_service
    log ""

    log ""

    log "${GREEN}========================================${NC}"
    log "${GREEN}Fresh installation completed!${NC}"
    log "${GREEN}========================================${NC}"
    log ""
    log "Platform URL: http://localhost"
    log ""
    log "Next steps:"
    log "1. Open http://localhost in a browser. The setup wizard runs on"
    log "   first visit and creates the administrator account."
    log ""
    log "   The wizard asks for this setup token:"
    log ""
    log "       ${BOLD}${SETUP_TOKEN}${NC}"
    log ""
    log "   It is also in $PLATFORM_DIR/.env. Nobody can claim the admin"
    log "   account without it. Delete the line once your admin exists."
    log "2. Link labs to curriculum (see LAB_DEPLOYMENT.md)"
    log ""
    log "VPN settings (endpoint, public key) can be changed"
    log "from the admin panel: Settings → Vpn"
}

# Create comprehensive backup before upgrade
create_upgrade_backup() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_path="$PLATFORM_DIR/.backups/pre-upgrade-$timestamp"
    
    log "${BLUE}Creating comprehensive backup before upgrade...${NC}"
    log "${YELLOW}Backup location: $backup_path${NC}"
    
    mkdir -p "$backup_path"
    
    # Backup critical configuration files
    log "Backing up configuration files..."
    if [ -f "$PLATFORM_DIR/.env" ]; then
        cp "$PLATFORM_DIR/.env" "$backup_path/.env"
        log "  ✓ .env"
    fi
    
    if [ -f "$PLATFORM_DIR/docker-compose.yml" ]; then
        cp "$PLATFORM_DIR/docker-compose.yml" "$backup_path/docker-compose.yml"
        log "  ✓ docker-compose.yml"
    fi
    
    # Backup backend directory
    if [ -d "$PLATFORM_DIR/backend" ]; then
        log "Backing up backend directory..."
        cp -r "$PLATFORM_DIR/backend" "$backup_path/backend"
        log "  ✓ backend/ (full directory)"
    fi
    
    # Backup frontend directory
    if [ -d "$PLATFORM_DIR/frontend" ]; then
        log "Backing up frontend directory..."
        cp -r "$PLATFORM_DIR/frontend" "$backup_path/frontend"
        log "  ✓ frontend/ (full directory)"
    fi
    
    # Backup any custom scripts or configs
    if [ -d "$PLATFORM_DIR/scripts" ]; then
        log "Backing up custom scripts..."
        cp -r "$PLATFORM_DIR/scripts" "$backup_path/scripts" 2>/dev/null || true
        log "  ✓ scripts/ (if exists)"
    fi
    
    # Backup database dump (if containers are running)
    if docker compose -f "$PLATFORM_DIR/docker-compose.yml" ps db 2>/dev/null | grep -q "Up"; then
        log "Backing up database..."
        mkdir -p "$backup_path/database"
        if docker compose -f "$PLATFORM_DIR/docker-compose.yml" exec -T db pg_dump -U labuser labdb > "$backup_path/database/labdb.sql" 2>/dev/null; then
            log "  ✓ database/labdb.sql"
        else
            log "  ${YELLOW}⚠ Database backup failed (database may not be accessible)${NC}"
        fi
    else
        log "  ${YELLOW}⚠ Database container not running, skipping database backup${NC}"
    fi
    
    # Create backup manifest
    cat > "$backup_path/BACKUP_MANIFEST.txt" << EOF
OpenCyberRange - Upgrade Backup
===================================
Backup Date: $(date)
Backup Location: $backup_path
Platform Directory: $PLATFORM_DIR

Backed Up Files:
- .env (configuration)
- docker-compose.yml (container definitions)
- backend/ (full directory)
- frontend/ (full directory)
- scripts/ (if exists)
- database/labdb.sql (if database was accessible)

To restore from this backup:
1. Stop containers: docker compose down
2. Restore files from: $backup_path
3. Restore database: docker compose exec -T db psql -U labuser labdb < database/labdb.sql
4. Restart: docker compose up -d

EOF
    
    log "${GREEN}✓ Comprehensive backup created${NC}"
    log "${CYAN}Backup location: $backup_path${NC}"
    echo "$backup_path"
}

# Update mode workflow
update_mode() {
    log "${CYAN}========================================${NC}"
    log "${CYAN}Update Mode${NC}"
    log "${CYAN}========================================${NC}"
    log ""
    log "${YELLOW}Existing .env file will be preserved${NC}"
    log ""
    
    # Create comprehensive backup before upgrade
    local backup_path=$(create_upgrade_backup)
    log ""
    
    # Use existing deploy script with appropriate flags
    if [ -f "$REPO_DIR/scripts/deploy-updates.sh" ]; then
        log "Running update deployment script..."
        bash "$REPO_DIR/scripts/deploy-updates.sh" --all
    else
        error_exit "deploy-updates.sh not found"
    fi
    
    log ""
    log "${GREEN}Backup saved to: $backup_path${NC}"
    log "${YELLOW}If anything goes wrong, restore from the backup${NC}"
}

# ── Banner ────────────────────────────────────────────────────────────────────
show_banner() {
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
    echo -e "${BOLD}${MAGENTA}    ║${NC}${DIM}   Platform Installer                 ${MAGENTA}${BOLD}║${NC}"
    echo -e "${BOLD}${MAGENTA}    ╚═══════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  ${DIM}Installs or updates the Docker-based platform${NC}"
    echo -e "  ${DIM}(backend, frontend, database).${NC}"
    echo ""
}

# Main execution
run_once() {
    # Pre-flight checks
    preflight_checks
    log ""

    # Execute based on mode
    if [ "$FRESH_INSTALL" = true ]; then
        fresh_install
    elif [ "$UPDATE_PLATFORM" = true ] || [ "$UPDATE_ALL" = true ]; then
        update_mode
    fi

    log ""
    log "${GREEN}========================================${NC}"
    log "${GREEN}Operation completed!${NC}"
    log "${GREEN}========================================${NC}"
    log ""
    log "Installation log: $LOG_FILE"
}

main() {
    show_banner

    # Non-interactive mode when called with CLI flags
    if [ "$CLI_MODE" = "fresh" ]; then
        FRESH_INSTALL=true
        UPDATE_ALL=true
        run_once
        return
    elif [ "$CLI_MODE" = "update" ]; then
        UPDATE_PLATFORM=true
        UPDATE_ALL=true
        run_once
        return
    fi

    # Interactive mode — loop back to menu after each action
    while true; do
        FRESH_INSTALL=false
        UPDATE_PLATFORM=false
        UPDATE_ALL=false

        show_menu
        log ""
        run_once
        log ""
        read -rp "Press Enter to return to the menu..." _
    done
}

# Run main function
main

