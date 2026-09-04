"""Edition entitlement for the platform-plus-modules model.

A plain JSON file declares the install's caps. No file means OCR-Lite
defaults. The file is an honesty gate backed by license terms, not a
security boundary; the content boundary (which packs are installed) is
what carries the business model. See PRD-OCR-Editions.md section 5.5.

File format (all keys optional; unknown keys ignored):

    {
      "edition": "enterprise",
      "max_privileged_accounts": null,
      "max_active_courses": null
    }

A cap value of null means unlimited. The path comes from the
OCR_ENTITLEMENT_FILE env var, defaulting to data/entitlement.json under
the app root.
"""
import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

LITE_DEFAULTS = {
    "edition": "lite",
    "max_privileged_accounts": 1,
    "max_active_courses": 5,
    "modules": [],   # optional code modules this tier ships (e.g. ["soc"])
}

_ALLOWED_KEYS = set(LITE_DEFAULTS.keys())

_entitlement: Optional[dict] = None


def _default_path() -> str:
    app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(app_root, "data", "entitlement.json")


def _load() -> dict:
    path = os.environ.get("OCR_ENTITLEMENT_FILE") or _default_path()
    try:
        with open(path) as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("entitlement root must be a JSON object")
        ent = dict(LITE_DEFAULTS)
        ent.update({k: v for k, v in data.items() if k in _ALLOWED_KEYS})
        logger.info(
            "Entitlement loaded from %s: edition=%s privileged=%s courses=%s",
            path, ent["edition"],
            ent["max_privileged_accounts"], ent["max_active_courses"],
        )
        return ent
    except FileNotFoundError:
        logger.info("No entitlement file at %s; OCR-Lite defaults apply", path)
        return dict(LITE_DEFAULTS)
    except Exception as exc:
        logger.warning(
            "Entitlement file %s unreadable (%s); OCR-Lite defaults apply",
            path, exc,
        )
        return dict(LITE_DEFAULTS)


def get_entitlement() -> dict:
    """Cached entitlement for this process (read once per worker)."""
    global _entitlement
    if _entitlement is None:
        _entitlement = _load()
    return _entitlement


def privileged_account_limit() -> Optional[int]:
    """Max instructor/admin accounts, or None for unlimited."""
    return get_entitlement().get("max_privileged_accounts")


def active_course_limit() -> Optional[int]:
    """Max non-archived courses, or None for unlimited."""
    return get_entitlement().get("max_active_courses")


def edition_name() -> str:
    return get_entitlement().get("edition", "lite")



def modules() -> list:
    """Optional code modules this tier ships (e.g. ['soc']). Written by the
    release pipeline from the tier's module list; drives the first-boot enable
    of module_<x>_enabled."""
    return list(get_entitlement().get("modules", []) or [])
