#!/bin/bash
# Database initialization script
# Sets up the complete database schema for the OpenCyberRange platform

set -e

# Determine platform directory
# If PLATFORM_DIR is set, use it
# Otherwise, try to detect from current directory or use default
if [ -z "$PLATFORM_DIR" ]; then
    # Check if we're already in the platform directory
    if [ -f "docker-compose.yml" ]; then
        PLATFORM_DIR="$(pwd)"
    else
        # Auto-detect from script location (scripts/ is inside platform/)
        PLATFORM_DIR="$(cd "$(dirname "$0")/.." && pwd)"
    fi
fi

if [ ! -f "$PLATFORM_DIR/docker-compose.yml" ]; then
    echo "Error: docker-compose.yml not found at $PLATFORM_DIR"
    echo "Please run this script from the platform directory or set PLATFORM_DIR environment variable."
    exit 1
fi

cd "$PLATFORM_DIR"

echo "=========================================="
echo "OpenCyberRange - Database Initialization"
echo "=========================================="
echo ""

# Wait for database to be ready
echo "Waiting for database to be ready..."
for i in {1..30}; do
    if docker compose exec -T db pg_isready -U labuser > /dev/null 2>&1; then
        break
    fi
    sleep 1
done

echo "Syncing database password with environment..."
# POSTGRES_PASSWORD only takes effect on initial initdb. If the data volume
# persists across reinstalls, the stored password can diverge from .env.
# This ALTER USER ensures they stay in sync.
if [ -f "$PLATFORM_DIR/.env" ]; then
    DB_PASS=$(grep '^POSTGRES_PASSWORD=' "$PLATFORM_DIR/.env" | cut -d= -f2-)
    if [ -n "$DB_PASS" ]; then
        docker compose exec -T db psql -U labuser -d labdb -tAc \
            "ALTER USER labuser WITH PASSWORD '${DB_PASS}';" >/dev/null 2>&1 && \
            echo "✓ Database password synced" || \
            echo "⚠ Could not sync password (non-fatal, entrypoint wrapper will handle it)"
    fi
fi
echo ""

echo "Initializing database schema..."
echo ""

docker compose exec -T db psql -U labuser -d labdb << 'EOSQL'

-- Create tracks table
CREATE TABLE IF NOT EXISTS tracks (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(150) UNIQUE NOT NULL,
    description TEXT,
    icon VARCHAR(50),
    color VARCHAR(20),
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create levels table
CREATE TABLE IF NOT EXISTS levels (
    id SERIAL PRIMARY KEY,
    track_id INTEGER REFERENCES tracks(id) ON DELETE CASCADE,
    level_number INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    sort_order INTEGER DEFAULT 0,
    UNIQUE(track_id, level_number)
);

-- Create index for levels
CREATE INDEX IF NOT EXISTS ix_level_track_number ON levels(track_id, level_number);

-- Modify labs table - add curriculum columns
ALTER TABLE labs ADD COLUMN IF NOT EXISTS level_id INTEGER REFERENCES levels(id);
ALTER TABLE labs ADD COLUMN IF NOT EXISTS sort_order INTEGER DEFAULT 0;
ALTER TABLE labs ADD COLUMN IF NOT EXISTS flag_hash VARCHAR(255);
ALTER TABLE labs ADD COLUMN IF NOT EXISTS hints TEXT;
ALTER TABLE labs ADD COLUMN IF NOT EXISTS tools TEXT;
ALTER TABLE labs ADD COLUMN IF NOT EXISTS hostnames TEXT;
ALTER TABLE labs ADD COLUMN IF NOT EXISTS scenario TEXT;
ALTER TABLE labs ADD COLUMN IF NOT EXISTS scenario_brief TEXT;
ALTER TABLE labs ADD COLUMN IF NOT EXISTS provides_kali_terminal BOOLEAN DEFAULT FALSE;
ALTER TABLE labs ADD COLUMN IF NOT EXISTS is_course_exclusive BOOLEAN DEFAULT FALSE;
ALTER TABLE labs ADD COLUMN IF NOT EXISTS is_course_available BOOLEAN DEFAULT FALSE;
ALTER TABLE labs ADD COLUMN IF NOT EXISTS visibility VARCHAR(20) DEFAULT 'public' NOT NULL;
ALTER TABLE labs ADD COLUMN IF NOT EXISTS created_by INTEGER REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE labs ADD COLUMN IF NOT EXISTS workbook VARCHAR(255);

-- Create lab_completions table
CREATE TABLE IF NOT EXISTS lab_completions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    lab_id INTEGER REFERENCES labs(id) ON DELETE CASCADE,
    completed_at TIMESTAMP DEFAULT NOW(),
    flag_submitted VARCHAR(100),
    attempts INTEGER DEFAULT 1,
    hints_used INTEGER DEFAULT 0,
    time_spent_minutes INTEGER,
    started_at TIMESTAMP
);

-- Create unique index for completions
CREATE UNIQUE INDEX IF NOT EXISTS ix_completion_user_lab ON lab_completions(user_id, lab_id);

-- Add started_at column to existing lab_completions table (for time-based hints)
ALTER TABLE lab_completions ADD COLUMN IF NOT EXISTS started_at TIMESTAMP;

-- Create flag_attempts table
CREATE TABLE IF NOT EXISTS flag_attempts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    lab_id INTEGER REFERENCES labs(id) ON DELETE CASCADE,
    flag_submitted VARCHAR(100),
    is_correct BOOLEAN DEFAULT FALSE,
    attempted_at TIMESTAMP DEFAULT NOW()
);

-- Create index for flag attempts
CREATE INDEX IF NOT EXISTS ix_attempt_user_lab_time ON flag_attempts(user_id, lab_id, attempted_at);

-- Add VPN support to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS vpn_registered BOOLEAN DEFAULT FALSE;

-- Add must_change_password column to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN DEFAULT FALSE;

-- Add role column for RBAC (student/instructor/admin)
ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'student' NOT NULL;
-- Backfill: existing admins get role='admin'
UPDATE users SET role = 'admin' WHERE is_admin = TRUE AND role = 'student';
-- Backfill: ensure consistency
UPDATE users SET role = 'student' WHERE is_admin = FALSE AND role NOT IN ('student', 'instructor');

-- Create wireguard_configs table for VPN configurations
CREATE TABLE IF NOT EXISTS wireguard_configs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    private_key VARCHAR(256) NOT NULL,
    public_key VARCHAR(100) NOT NULL,
    client_ip VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create index for wireguard_configs
CREATE INDEX IF NOT EXISTS ix_wireguard_configs_user_id ON wireguard_configs(user_id);

-- Widen private_key column if it was created at the old size
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'wireguard_configs' AND column_name = 'private_key'
          AND character_maximum_length < 256
    ) THEN
        ALTER TABLE wireguard_configs ALTER COLUMN private_key TYPE VARCHAR(256);
    END IF;
END $$;

-- Create courses table
CREATE TABLE IF NOT EXISTS courses (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    code VARCHAR(20) NOT NULL,
    semester VARCHAR(20) NOT NULL,
    description TEXT,
    invite_code VARCHAR(20) UNIQUE NOT NULL,
    instructor_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    is_archived BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Add wiki columns to courses (idempotent)
ALTER TABLE courses ADD COLUMN IF NOT EXISTS wiki_slug VARCHAR(50);
ALTER TABLE courses ADD COLUMN IF NOT EXISTS wiki_theme_color VARCHAR(30) DEFAULT 'blue';

-- Create course_enrollments table
CREATE TABLE IF NOT EXISTS course_enrollments (
    id SERIAL PRIMARY KEY,
    course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    enrolled_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(course_id, user_id)
);

-- Create course_lab_assignments table
CREATE TABLE IF NOT EXISTS course_lab_assignments (
    id SERIAL PRIMARY KEY,
    course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    lab_id INTEGER NOT NULL REFERENCES labs(id) ON DELETE CASCADE,
    sort_order INTEGER DEFAULT 0,
    display_name VARCHAR(255),
    assigned_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(course_id, lab_id)
);
CREATE INDEX IF NOT EXISTS ix_course_lab_assignment ON course_lab_assignments(course_id, lab_id);

-- Create assignments table
CREATE TABLE IF NOT EXISTS assignments (
    id SERIAL PRIMARY KEY,
    course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    name VARCHAR(150) NOT NULL,
    description TEXT,
    due_date TIMESTAMP,
    start_date TIMESTAMP,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create assignment_labs table
CREATE TABLE IF NOT EXISTS assignment_labs (
    id SERIAL PRIMARY KEY,
    assignment_id INTEGER NOT NULL REFERENCES assignments(id) ON DELETE CASCADE,
    lab_id INTEGER NOT NULL REFERENCES labs(id) ON DELETE CASCADE,
    sort_order INTEGER DEFAULT 0,
    UNIQUE(assignment_id, lab_id)
);
CREATE INDEX IF NOT EXISTS ix_assignment_lab ON assignment_labs(assignment_id, lab_id);

-- Create achievements table
CREATE TABLE IF NOT EXISTS achievements (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    course_id INTEGER REFERENCES courses(id) ON DELETE CASCADE,
    lab_id INTEGER REFERENCES labs(id) ON DELETE SET NULL,
    achievement_type VARCHAR(50) NOT NULL,
    awarded_at TIMESTAMP DEFAULT NOW()
);

-- Create course_completion_resets table
CREATE TABLE IF NOT EXISTS course_completion_resets (
    id SERIAL PRIMARY KEY,
    course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    lab_id INTEGER NOT NULL REFERENCES labs(id) ON DELETE CASCADE,
    reset_at TIMESTAMP DEFAULT NOW(),
    reset_by INTEGER REFERENCES users(id) ON DELETE SET NULL
);

-- Modify lab_sessions table - add Kali terminal fields
ALTER TABLE lab_sessions ADD COLUMN IF NOT EXISTS kali_container_id VARCHAR(100);
ALTER TABLE lab_sessions ADD COLUMN IF NOT EXISTS kali_terminal_url VARCHAR(255);
ALTER TABLE lab_sessions ADD COLUMN IF NOT EXISTS kali_port INTEGER;
ALTER TABLE lab_sessions ADD COLUMN IF NOT EXISTS kali_last_activity TIMESTAMP;
ALTER TABLE lab_sessions ADD COLUMN IF NOT EXISTS kali_activity_heartbeat TIMESTAMP;

EOSQL

if [ $? -eq 0 ]; then
    echo "✓ Database schema initialized successfully"
else
    echo "✗ Failed to initialize database schema"
    exit 1
fi

echo ""
echo "Verifying schema..."
docker compose exec -T db psql -U labuser -d labdb -c "\dt" > /dev/null

echo ""
echo "=========================================="
echo "Database initialization complete!"
echo "=========================================="
echo ""

