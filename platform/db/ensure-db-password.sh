#!/bin/bash
# ==============================================================================
# ensure-db-password.sh — Wrapper entrypoint for the PostgreSQL container
# ==============================================================================
#
# Problem: POSTGRES_PASSWORD only sets the password during initial initdb.
#          If the data volume persists but the .env is regenerated (e.g., on
#          reinstall), the stored password diverges from the environment
#          variable. The backend then fails to authenticate over the network
#          (where scram-sha-256 is enforced), causing a crash loop.
#
# Fix:     This wrapper starts a background task that waits for PostgreSQL to
#          accept connections, then runs ALTER USER to sync the password with
#          the current POSTGRES_PASSWORD env var. It then exec's the original
#          docker-entrypoint.sh so PostgreSQL runs as PID 1.
#
# ==============================================================================

set -e

# Sync the password in the background after postgres starts
(
    # Wait for PostgreSQL to accept connections
    for i in $(seq 1 30); do
        if pg_isready -U "${POSTGRES_USER:-labuser}" >/dev/null 2>&1; then
            # Escape single quotes in the password for SQL safety
            ESCAPED_PASSWORD=$(printf '%s' "$POSTGRES_PASSWORD" | sed "s/'/''/g")

            psql -U "${POSTGRES_USER:-labuser}" -d "${POSTGRES_DB:-labdb}" -tAc \
                "ALTER USER \"${POSTGRES_USER:-labuser}\" WITH PASSWORD '${ESCAPED_PASSWORD}';" \
                >/dev/null 2>&1 || true
            break
        fi
        sleep 1
    done
) &

# Hand off to the real PostgreSQL entrypoint (becomes PID 1)
# Pass through any CMD arguments (e.g. -c max_connections=300)
exec docker-entrypoint.sh "$@"
