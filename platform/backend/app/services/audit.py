"""
Audit logging service for tracking administrative actions.
Provides comprehensive logging with actor information for security compliance.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import json

# Configure audit logger
logger = logging.getLogger("audit")
logger.setLevel(logging.INFO)

# Create file handler for audit log (if not already configured)
# In production, this would write to /var/log/opencyberrange/audit.log
# For development/containerized deployment, we'll also log to console
if not logger.handlers:
    # Console handler for containerized deployment
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - AUDIT - %(message)s'
    ))
    logger.addHandler(console_handler)


def log_admin_action(
    action: str,
    admin_user_id: int,
    admin_username: str,
    target_type: str,
    target_id: Optional[int] = None,
    target_identifier: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None
):
    """
    Log an administrative action for audit purposes.
    
    Args:
        action: The action performed (e.g., "USER_CREATED", "PASSWORD_RESET", "SESSION_TERMINATED")
        admin_user_id: ID of the admin performing the action
        admin_username: Username of the admin
        target_type: Type of target (e.g., "user", "lab", "session")
        target_id: ID of the target resource
        target_identifier: Human-readable identifier (e.g., username)
        details: Additional details about the action
        ip_address: IP address of the admin
    """
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "admin": {
            "id": admin_user_id,
            "username": admin_username
        },
        "target": {
            "type": target_type,
            "id": target_id,
            "identifier": target_identifier
        },
        "ip_address": ip_address,
        "details": details or {}
    }
    
    # Log structured JSON for easy parsing
    logger.info(json.dumps(log_entry))


# Common audit actions
class AuditActions:
    """Standard audit action names for consistency"""
    # User management
    USER_CREATED = "USER_CREATED"
    USER_UPDATED = "USER_UPDATED"
    USER_DELETED = "USER_DELETED"
    USER_APPROVED = "USER_APPROVED"
    USER_UNLOCKED = "USER_UNLOCKED"
    PASSWORD_RESET = "PASSWORD_RESET"
    
    # Lab management
    LAB_ACTIVATED = "LAB_ACTIVATED"
    LAB_DEACTIVATED = "LAB_DEACTIVATED"
    LAB_UPDATED = "LAB_UPDATED"
    LAB_RESET = "LAB_RESET"
    LAB_FLAG_REVEALED = "LAB_FLAG_REVEALED"
    
    # Session management
    SESSION_TERMINATED = "SESSION_TERMINATED"
    ALL_SESSIONS_TERMINATED = "ALL_SESSIONS_TERMINATED"
    SESSION_HISTORY_CLEARED = "SESSION_HISTORY_CLEARED"
    STALE_SESSION_RESET = "STALE_SESSION_RESET"

    # VPN / Firewall management
    FIREWALL_RULES_APPLIED = "FIREWALL_RULES_APPLIED"
    VPN_PEER_RESYNCED = "VPN_PEER_RESYNCED"
    VPN_PEER_REGISTERED = "VPN_PEER_REGISTERED"
    VPN_PEER_REMOVED = "VPN_PEER_REMOVED"
    VPN_PEERS_SYNCED = "VPN_PEERS_SYNCED"
    
    # Container management
    CLEANUP_ORPHANED_CONTAINERS = "CLEANUP_ORPHANED_CONTAINERS"
    LAB_IMAGE_DELETED = "LAB_IMAGE_DELETED"
    IMAGES_PRUNED = "IMAGES_PRUNED"
    BUILD_CACHE_PRUNED = "BUILD_CACHE_PRUNED"

    # Settings management
    SETTINGS_UPDATED = "SETTINGS_UPDATED"

    # Curriculum management
    TRACK_CREATED = "TRACK_CREATED"
    TRACK_UPDATED = "TRACK_UPDATED"
    TRACK_DELETED = "TRACK_DELETED"
    LEVEL_CREATED = "LEVEL_CREATED"
    LEVEL_UPDATED = "LEVEL_UPDATED"
    LEVEL_DELETED = "LEVEL_DELETED"
    LAB_CREATED = "LAB_CREATED"

    # Setup
    SETUP_COMPLETED = "SETUP_COMPLETED"

