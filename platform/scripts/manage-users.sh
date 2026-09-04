#!/bin/bash
# OpenCyberRange - User Management Script
# Allows resetting passwords and changing user roles

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
# Auto-detect from script location (scripts/ is inside platform/)
PLATFORM_DIR="${PLATFORM_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
LOG_FILE="$PLATFORM_DIR/.backups/user-management.log"

# Logging function
log() {
    echo -e "$1" | tee -a "$LOG_FILE"
}

# Error handling
error_exit() {
    log "${RED}ERROR: $1${NC}"
    exit 1
}

# Check if platform directory exists
if [ ! -d "$PLATFORM_DIR" ]; then
    error_exit "Platform directory not found: $PLATFORM_DIR"
fi

# Check if docker-compose.yml exists
if [ ! -f "$PLATFORM_DIR/docker-compose.yml" ]; then
    error_exit "docker-compose.yml not found in $PLATFORM_DIR"
fi

cd "$PLATFORM_DIR"

# Generate password hash
generate_password_hash() {
    local password="$1"
    
    # Check if backend container is running
    if ! docker compose ps backend | grep -q "Up"; then
        error_exit "Backend container is not running. Start it with: docker compose up -d backend"
    fi
    
    # Try to generate hash
    local hash=$(docker compose exec -T backend python3 -c "
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
print(pwd_context.hash('$password'))
" 2>&1)
    
    # Check if hash was generated (should start with $2b$)
    if [[ "$hash" =~ ^\$2b\$ ]]; then
        echo "$hash"
    else
        error_exit "Failed to generate password hash. Error: $hash"
    fi
}

# List all users
list_users() {
    log "${BLUE}Current Users:${NC}"
    log ""
    docker compose exec -T db psql -U labuser -d labdb -c "
SELECT
    id,
    username,
    email,
    student_id,
    role,
    is_admin,
    is_approved,
    is_locked,
    failed_attempts,
    created_at
FROM users
ORDER BY id;
" 2>&1 | tee -a "$LOG_FILE"
    log ""
}

# Reset user password
reset_password() {
    local username="$1"
    local new_password="$2"
    
    if [ -z "$username" ] || [ -z "$new_password" ]; then
        error_exit "Username and password are required"
    fi
    
    # Check if user exists
    local user_exists=$(docker compose exec -T db psql -U labuser -d labdb -t -c "SELECT COUNT(*) FROM users WHERE username = '$username';" 2>/dev/null | tr -d ' ')
    if [ "$user_exists" != "1" ]; then
        error_exit "User not found: $username"
    fi
    
    log "${BLUE}Generating password hash...${NC}"
    local hash=$(generate_password_hash "$new_password")
    
    if [ -z "$hash" ]; then
        error_exit "Failed to generate password hash"
    fi
    
    log "${BLUE}Resetting password for user: $username${NC}"
    
    # Use psql with proper escaping for the hash (which contains $ characters)
    # We'll use a here-document to avoid shell escaping issues
    docker compose exec -T db psql -U labuser -d labdb <<EOF
UPDATE users 
SET 
    hashed_password = '$hash',
    is_locked = false,
    failed_attempts = 0,
    locked_at = NULL
WHERE username = '$username';
EOF
    
    if [ $? -ne 0 ]; then
        error_exit "Failed to update password in database"
    fi
    
    # Verify the password was updated
    local stored_hash=$(docker compose exec -T db psql -U labuser -d labdb -t -A -c "SELECT hashed_password FROM users WHERE username = '$username';" 2>/dev/null | head -n1)
    
    if [ -z "$stored_hash" ]; then
        error_exit "Failed to verify password update"
    fi
    
    log "${GREEN}✓ Password reset successfully for user: $username${NC}"
    log "${YELLOW}New password: $new_password${NC}"
    
    # Test password verification (only if backend is running)
    if docker compose ps backend 2>/dev/null | grep -q "Up"; then
        log "${BLUE}Verifying password hash...${NC}"
        local verify_result=$(docker compose exec -T backend python3 <<PYTHON_SCRIPT 2>&1
from passlib.context import CryptContext
import sys

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
password = '''$new_password'''
stored_hash = '''$stored_hash'''

try:
    if pwd_context.verify(password, stored_hash):
        print('OK')
        sys.exit(0)
    else:
        print('FAIL')
        sys.exit(1)
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
PYTHON_SCRIPT
)
        
        if [[ "$verify_result" == *"OK"* ]]; then
            log "${GREEN}✓ Password verification successful${NC}"
        else
            log "${YELLOW}⚠ Note: Password verification unavailable (backend may be restarting)${NC}"
            log "${YELLOW}The password was reset successfully. Try logging in to confirm.${NC}"
        fi
    else
        log "${YELLOW}⚠ Note: Backend container not running - skipping verification${NC}"
        log "${YELLOW}The password was reset successfully. Start backend and try logging in to confirm.${NC}"
    fi
}

# Change user role
change_role() {
    local username="$1"
    local is_admin="$2"
    local is_approved="$3"
    local is_active="$4"
    local role="$5"

    if [ -z "$username" ]; then
        error_exit "Username is required"
    fi

    log "${BLUE}Updating role for user: $username${NC}"

    local sql="UPDATE users SET"
    local updates=()

    if [ -n "$role" ]; then
        updates+=("role = '$role'")
        # Keep is_admin in sync
        if [ "$role" = "admin" ]; then
            updates+=("is_admin = true")
        else
            updates+=("is_admin = false")
        fi
    elif [ -n "$is_admin" ]; then
        updates+=("is_admin = $is_admin")
        # Keep role in sync
        if [ "$is_admin" = "true" ]; then
            updates+=("role = 'admin'")
        else
            updates+=("role = 'student'")
        fi
    fi

    if [ -n "$is_approved" ]; then
        updates+=("is_approved = $is_approved")
    fi

    # Only update is_active if column exists (check first)
    if [ -n "$is_active" ]; then
        local has_is_active=$(docker compose exec -T db psql -U labuser -d labdb -t -c "
            SELECT COUNT(*) FROM information_schema.columns
            WHERE table_name='users' AND column_name='is_active';
        " 2>/dev/null | tr -d ' ')

        if [ "$has_is_active" = "1" ]; then
            updates+=("is_active = $is_active")
        else
            log "${YELLOW}Note: is_active column does not exist in database, skipping${NC}"
        fi
    fi

    if [ ${#updates[@]} -eq 0 ]; then
        error_exit "No role changes specified"
    fi

    sql="$sql $(IFS=,; echo "${updates[*]}") WHERE username = '$username';"

    docker compose exec -T db psql -U labuser -d labdb -c "$sql" > /dev/null 2>&1

    local updated=$(docker compose exec -T db psql -U labuser -d labdb -t -c "SELECT COUNT(*) FROM users WHERE username = '$username';" | tr -d ' ')

    if [ "$updated" = "1" ]; then
        log "${GREEN}✓ Role updated successfully for user: $username${NC}"
    else
        error_exit "User not found: $username"
    fi
}

# Unlock user account
unlock_user() {
    local username="$1"
    
    if [ -z "$username" ]; then
        error_exit "Username is required"
    fi
    
    log "${BLUE}Unlocking user account: $username${NC}"
    
    docker compose exec -T db psql -U labuser -d labdb <<EOF
UPDATE users 
SET 
    is_locked = false,
    failed_attempts = 0,
    locked_at = NULL
WHERE username = '$username';
EOF
    
    if [ $? -eq 0 ]; then
        log "${GREEN}✓ User account unlocked: $username${NC}"
    else
        error_exit "Failed to unlock user account"
    fi
}

# Fix user (reset password, unlock, and approve in one operation)
fix_user() {
    local username="$1"
    local new_password="$2"
    
    if [ -z "$username" ] || [ -z "$new_password" ]; then
        error_exit "Username and password are required"
    fi
    
    # Check if user exists
    local user_exists=$(docker compose exec -T db psql -U labuser -d labdb -t -c "SELECT COUNT(*) FROM users WHERE username = '$username';" 2>/dev/null | tr -d ' ')
    if [ "$user_exists" != "1" ]; then
        error_exit "User not found: $username"
    fi
    
    log "${BLUE}Fixing user account: $username${NC}"
    log "${BLUE}This will: reset password, unlock account, and approve user${NC}"
    
    # Generate password hash
    log "${BLUE}Generating password hash...${NC}"
    local hash=$(generate_password_hash "$new_password")
    
    if [ -z "$hash" ]; then
        error_exit "Failed to generate password hash"
    fi
    
    # Update user with all fixes
    docker compose exec -T db psql -U labuser -d labdb <<EOF
UPDATE users 
SET 
    hashed_password = '$hash',
    is_locked = false,
    failed_attempts = 0,
    locked_at = NULL,
    is_approved = true
WHERE username = '$username';
EOF
    
    if [ $? -ne 0 ]; then
        error_exit "Failed to update user in database"
    fi
    
    # Verify password
    log "${BLUE}Verifying password hash...${NC}"
    local stored_hash=$(docker compose exec -T db psql -U labuser -d labdb -t -A -c "SELECT hashed_password FROM users WHERE username = '$username';" 2>/dev/null | head -n1)
    
    local verify_result=$(docker compose exec -T backend python3 <<PYTHON_SCRIPT
from passlib.context import CryptContext
import sys

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
password = '''$new_password'''
stored_hash = '''$stored_hash'''

try:
    if pwd_context.verify(password, stored_hash):
        print('OK')
        sys.exit(0)
    else:
        print('FAIL')
        sys.exit(1)
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
PYTHON_SCRIPT
)
    
    if [[ "$verify_result" == *"OK"* ]]; then
        log "${GREEN}✓ User fixed successfully: $username${NC}"
        log "${GREEN}✓ Password reset, account unlocked, and user approved${NC}"
        log "${GREEN}✓ Password verification successful${NC}"
        log "${YELLOW}New password: $new_password${NC}"
    else
        log "${RED}⚠ Warning: Password verification failed${NC}"
        log "${YELLOW}Note: The user was updated, but verification had issues. Try logging in to confirm.${NC}"
    fi
}

# Create new user
create_user() {
    local username="$1"
    local email="$2"
    local student_id="$3"
    local password="$4"
    local is_admin="${5:-false}"
    local is_approved="${6:-true}"
    
    if [ -z "$username" ] || [ -z "$email" ] || [ -z "$student_id" ] || [ -z "$password" ]; then
        error_exit "Username, email, student_id, and password are required"
    fi
    
    # Check if user already exists
    local existing=$(docker compose exec -T db psql -U labuser -d labdb -t -c "SELECT COUNT(*) FROM users WHERE username = '$username';" 2>/dev/null | tr -d ' ')
    if [ "$existing" = "1" ]; then
        error_exit "User already exists: $username. Use option 2 to reset password instead."
    fi
    
    log "${BLUE}Creating new user: $username${NC}"
    
    local hash=$(generate_password_hash "$password")
    
    if [ -z "$hash" ]; then
        error_exit "Failed to generate password hash"
    fi
    
    # Check if is_active column exists
    local has_is_active=$(docker compose exec -T db psql -U labuser -d labdb -t -c "
        SELECT COUNT(*) FROM information_schema.columns 
        WHERE table_name='users' AND column_name='is_active';
    " 2>/dev/null | tr -d ' ')
    
    # Determine role from is_admin flag
    local role="student"
    if [ "$is_admin" = "true" ]; then
        role="admin"
    fi

    # Use here-document to avoid shell escaping issues with hash
    if [ "$has_is_active" = "1" ]; then
        docker compose exec -T db psql -U labuser -d labdb <<EOF
INSERT INTO users (username, email, student_id, hashed_password, is_admin, is_approved, is_active, is_locked, failed_attempts, role)
VALUES ('$username', '$email', '$student_id', '$hash', $is_admin, $is_approved, true, false, 0, '$role');
EOF
    else
        docker compose exec -T db psql -U labuser -d labdb <<EOF
INSERT INTO users (username, email, student_id, hashed_password, is_admin, is_approved, is_locked, failed_attempts, role)
VALUES ('$username', '$email', '$student_id', '$hash', $is_admin, $is_approved, false, 0, '$role');
EOF
    fi
    
    if [ $? -ne 0 ]; then
        error_exit "Failed to create user in database"
    fi
    
    local created=$(docker compose exec -T db psql -U labuser -d labdb -t -c "SELECT COUNT(*) FROM users WHERE username = '$username';" 2>/dev/null | tr -d ' ')
    
    if [ "$created" = "1" ]; then
        log "${GREEN}✓ User created successfully: $username${NC}"
        
        # Verify password hash
        log "${BLUE}Verifying password hash...${NC}"
        local stored_hash=$(docker compose exec -T db psql -U labuser -d labdb -t -A -c "SELECT hashed_password FROM users WHERE username = '$username';" 2>/dev/null | head -n1)
        
        local verify_result=$(docker compose exec -T backend python3 <<PYTHON_SCRIPT
from passlib.context import CryptContext
import sys

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
password = '''$password'''
stored_hash = '''$stored_hash'''

try:
    if pwd_context.verify(password, stored_hash):
        print('OK')
        sys.exit(0)
    else:
        print('FAIL')
        sys.exit(1)
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
PYTHON_SCRIPT
)
        
        if [[ "$verify_result" == *"OK"* ]]; then
            log "${GREEN}✓ Password verification successful${NC}"
        else
            log "${RED}⚠ Warning: Password verification failed${NC}"
            log "${YELLOW}Note: The user was created, but verification had issues. Try logging in to confirm.${NC}"
        fi
    else
        error_exit "Failed to create user (verification failed)"
    fi
}

# Show menu
show_menu() {
    log ""
    log "${CYAN}========================================${NC}"
    log "${CYAN}OpenCyberRange - User Management${NC}"
    log "${CYAN}========================================${NC}"
    log ""
    log "1) List all users"
    log "2) Reset user password"
    log "3) Set user role (student/instructor/admin)"
    log "4) Approve user"
    log "5) Unapprove user"
    log "6) Activate user"
    log "7) Deactivate user"
    log "8) Unlock user account"
    log "9) Create new user"
    log "10) Fix user (reset password + unlock + approve)"
    log "11) Exit"
    log ""
}

# Main menu loop
main() {
    while true; do
        show_menu
        read -p "Select an option [1-12]: " choice
        
        case $choice in
            1)
                list_users
                read -p "Press Enter to continue..."
                ;;
            2)
                log ""
                read -p "Enter username: " username
                read -sp "Enter new password: " password
                log ""
                reset_password "$username" "$password"
                log ""
                read -p "Press Enter to continue..."
                ;;
            3)
                log ""
                read -p "Enter username: " username
                log "Available roles: student, instructor, admin"
                read -p "Enter role: " role_choice
                if [[ "$role_choice" =~ ^(student|instructor|admin)$ ]]; then
                    change_role "$username" "" "" "" "$role_choice"
                else
                    log "${RED}Invalid role. Must be: student, instructor, or admin${NC}"
                fi
                log ""
                read -p "Press Enter to continue..."
                ;;
            4)
                log ""
                read -p "Enter username: " username
                change_role "$username" "" "true" ""
                log ""
                read -p "Press Enter to continue..."
                ;;
            5)
                log ""
                read -p "Enter username: " username
                change_role "$username" "" "false" ""
                log ""
                read -p "Press Enter to continue..."
                ;;
            6)
                log ""
                read -p "Enter username: " username
                change_role "$username" "" "" "true"
                log ""
                read -p "Press Enter to continue..."
                ;;
            7)
                log ""
                read -p "Enter username: " username
                change_role "$username" "" "" "false"
                log ""
                read -p "Press Enter to continue..."
                ;;
            8)
                log ""
                read -p "Enter username: " username
                unlock_user "$username"
                log ""
                read -p "Press Enter to continue..."
                ;;
            9)
                log ""
                read -p "Enter username: " username
                read -p "Enter email: " email
                read -p "Enter student ID: " student_id
                read -sp "Enter password: " password
                log ""
                log "Available roles: student, instructor, admin"
                read -p "Enter role (default: student): " role_choice
                role_choice="${role_choice:-student}"
                is_admin="false"
                if [ "$role_choice" = "admin" ]; then
                    is_admin="true"
                fi
                create_user "$username" "$email" "$student_id" "$password" "$is_admin"
                # Set the role explicitly if instructor
                if [ "$role_choice" = "instructor" ]; then
                    change_role "$username" "" "" "" "instructor"
                fi
                log ""
                read -p "Press Enter to continue..."
                ;;
            10)
                log ""
                read -p "Enter username: " username
                read -sp "Enter new password: " password
                log ""
                fix_user "$username" "$password"
                log ""
                read -p "Press Enter to continue..."
                ;;
            11)
                log "${BLUE}Exiting...${NC}"
                exit 0
                ;;
            *)
                log "${RED}Invalid option. Please select 1-11.${NC}"
                read -p "Press Enter to continue..."
                ;;
        esac
    done
}

# Run main function
main "$@"

