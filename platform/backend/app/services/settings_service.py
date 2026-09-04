"""
Platform settings service - provides cached read/write access to
runtime-configurable settings stored in the platform_settings table.

Settings fall back to config.py (environment) defaults when not
present in the database, so existing .env deployments keep working.
"""

import logging
import os
import time as _time
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.models import PlatformSetting

logger = logging.getLogger(__name__)

# In-memory cache with TTL: populated on first read, invalidated on write.
# The TTL ensures multi-worker deployments see fresh settings within
# _CACHE_TTL_SECONDS even if another worker performed the update.
_cache: Dict[str, str] = {}
_cache_loaded = False
_cache_loaded_at: float = 0.0
_CACHE_TTL_SECONDS = 30  # re-read from DB at most every 30 seconds

# Default settings with metadata.  These are seeded into the DB on
# first startup and serve as documentation for what's configurable.
DEFAULT_SETTINGS = [
    # --- General ---
    {"key": "setup_complete", "value": "false", "category": "general",
     "description": "Set to true after first-run setup wizard completes", "is_secret": False},

    # --- Security ---
    {"key": "jwt_expiration_hours", "value": "24", "category": "security",
     "description": "JWT token lifetime in hours"},
    {"key": "max_failed_attempts", "value": "5", "category": "security",
     "description": "Failed login attempts before account lockout"},
    {"key": "lockout_duration_minutes", "value": "30", "category": "security",
     "description": "Account lockout duration in minutes"},
    {"key": "require_approval", "value": "true", "category": "security",
     "description": "Require admin approval for new user registrations"},
    {"key": "enable_api_docs", "value": "false", "category": "security",
     "description": "Enable Swagger UI (/docs) and ReDoc (/redoc) on the backend API"},

    # --- Labs ---
    {"key": "default_session_hours", "value": "2", "category": "labs",
     "description": "Default exercise session duration in hours"},
    {"key": "max_session_hours", "value": "8", "category": "labs",
     "description": "Maximum exercise session duration in hours"},
    {"key": "container_cpu_limit", "value": "0.5", "category": "labs",
     "description": "Default CPU limit per container (Docker CPUs)"},
    {"key": "container_memory_limit", "value": "512M", "category": "labs",
     "description": "Default memory limit per container"},
    # --- VPN ---
    {"key": "vpn_enabled", "value": "true", "category": "vpn",
     "description": "Enable WireGuard VPN features"},
    {"key": "vpn_endpoint", "value": "", "category": "vpn",
     "description": "WireGuard server endpoint (host:port)"},
    {"key": "vpn_public_key", "value": "", "category": "vpn",
     "description": "WireGuard server public key"},
    {"key": "vpn_wstunnel_enabled", "value": "false", "category": "vpn",
     "description": "Wrap WireGuard in WebSocket tunnel (for Cloudflare Tunnel deployments)"},
    {"key": "vpn_wstunnel_url", "value": "", "category": "vpn",
     "description": "WebSocket tunnel URL (e.g. wss://vpn.yourdomain.com)"},





]

def _load_cache(db: Session) -> None:
    """Load all settings into memory cache."""
    global _cache, _cache_loaded, _cache_loaded_at
    rows = db.query(PlatformSetting).all()
    _cache = {row.key: row.value for row in rows}
    _cache_loaded = True
    _cache_loaded_at = _time.monotonic()


def _invalidate_cache() -> None:
    global _cache, _cache_loaded, _cache_loaded_at
    _cache = {}
    _cache_loaded = False
    _cache_loaded_at = 0.0


def _is_cache_stale() -> bool:
    """Return True if cache needs refreshing (expired TTL or never loaded)."""
    if not _cache_loaded:
        return True
    return (_time.monotonic() - _cache_loaded_at) > _CACHE_TTL_SECONDS


def get_setting(db: Session, key: str, default: Optional[str] = None) -> Optional[str]:
    """Get a single setting value (cached with TTL)."""
    if _is_cache_stale():
        _load_cache(db)
    return _cache.get(key, default)


def get_setting_fresh(db: Session, key: str, default: Optional[str] = None) -> Optional[str]:
    """Read a setting straight from the database, skipping the cache.

    The cache is per worker and only the worker that handled a write clears it,
    so every other worker can serve a stale value until the TTL expires. That is
    fine for a value that merely tunes behaviour, and wrong for one that gates
    access: an admin who switches something off would keep granting it for up to
    the TTL on most workers. Use this for those checks. The cost is one indexed
    single-row lookup.
    """
    row = db.query(PlatformSetting).filter(PlatformSetting.key == key).first()
    if row is None:
        return default
    return row.value


def get_settings_by_category(db: Session, category: str) -> List[dict]:
    """Return all settings in a category as list of dicts."""
    rows = db.query(PlatformSetting).filter(
        PlatformSetting.category == category
    ).order_by(PlatformSetting.key).all()
    return [
        {
            "key": r.key,
            "value": r.value if not r.is_secret else "••••••••",
            "category": r.category,
            "description": r.description,
            "is_secret": r.is_secret,
        }
        for r in rows
    ]


def get_all_settings(db: Session) -> List[dict]:
    """Return all settings grouped by category."""
    rows = db.query(PlatformSetting).order_by(
        PlatformSetting.category, PlatformSetting.key
    ).all()
    return [
        {
            "key": r.key,
            "value": r.value if not r.is_secret else "••••••••",
            "category": r.category,
            "description": r.description,
            "is_secret": r.is_secret,
        }
        for r in rows
    ]


def set_setting(db: Session, key: str, value: str) -> PlatformSetting:
    """Create or update a setting."""
    row = db.query(PlatformSetting).filter(PlatformSetting.key == key).first()
    if row:
        row.value = value
    else:
        row = PlatformSetting(key=key, value=value)
        db.add(row)
    db.commit()
    db.refresh(row)
    _invalidate_cache()
    return row


def bulk_update_settings(db: Session, updates: Dict[str, str]) -> int:
    """Update multiple settings at once. Returns count of updated rows."""
    count = 0
    for key, value in updates.items():
        row = db.query(PlatformSetting).filter(PlatformSetting.key == key).first()
        if row:
            row.value = value
            count += 1
        else:
            db.add(PlatformSetting(key=key, value=value))
            count += 1
    db.commit()
    _invalidate_cache()
    return count


def seed_defaults(db: Session) -> int:
    """Insert default settings that don't already exist. Returns count of new rows."""
    created = 0
    resynced = 0
    for defn in DEFAULT_SETTINGS:
        existing = db.query(PlatformSetting).filter(
            PlatformSetting.key == defn["key"]
        ).first()
        if not existing:
            db.add(PlatformSetting(
                key=defn["key"],
                value=defn["value"],
                category=defn.get("category", "general"),
                description=defn.get("description"),
                is_secret=defn.get("is_secret", False),
            ))
            created += 1
        else:
            # A setting's description and category are documentation owned by
            # the code, not admin data, so keep them in step with DEFAULT_SETTINGS
            # on every start. Without this an existing row keeps whatever text it
            # was first seeded with and the help an admin reads drifts from what
            # the setting actually does. The value is never touched: that is the
            # admin's.
            desc = defn.get("description")
            cat = defn.get("category", "general")
            if existing.description != desc or existing.category != cat:
                existing.description = desc
                existing.category = cat
                resynced += 1
    if created or resynced:
        db.commit()
        _invalidate_cache()
        if created:
            logger.info(f"Seeded {created} default platform settings")
        if resynced:
            logger.info(f"Resynced descriptions for {resynced} platform settings")

    # Populate empty VPN settings from environment variables so the
    # admin UI shows the values that were auto-detected during install.
    _ENV_TO_SETTING = {
        "vpn_endpoint": "WG_SERVER_ENDPOINT",
        "vpn_public_key": "WG_SERVER_PUBLIC_KEY",
    }
    updated = 0
    for setting_key, env_var in _ENV_TO_SETTING.items():
        env_val = os.environ.get(env_var, "")
        if not env_val:
            continue
        row = db.query(PlatformSetting).filter(
            PlatformSetting.key == setting_key
        ).first()
        if row and not row.value:
            row.value = env_val
            updated += 1
    if updated:
        db.commit()
        _invalidate_cache()
        logger.info(f"Populated {updated} VPN settings from environment")

    return created
