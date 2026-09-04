"""
Module status API.
Exposes which optional modules (SOC) are currently enabled.
Accessible to any authenticated user (sidebar visibility depends on this).
"""

import importlib.util

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_active_user
from app.models import User
from app.services import settings_service
from app import modules as module_registry

router = APIRouter()


def available_modules() -> dict:
    """Entitlement modules whose code is present in this edition.

    Sourced from the module manifests under app/modules/; editions that strip a
    module's files (and its manifest) drop out here automatically, so the module
    never surfaces in the setup wizard, admin settings, or the sidebar.
    """
    present = {m.name for m in module_registry.discover(present_only=True)}
    return {
        mid: meta
        for mid, meta in module_registry.known_modules().items()
        if mid in present
    }


@router.get("/")
async def get_modules_status(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """Return enabled/disabled status of the optional modules this build ships."""
    modules = {}
    for module_id, meta in available_modules().items():
        raw = settings_service.get_setting(db, meta["setting_key"], "false")
        modules[module_id] = {
            "enabled": raw.lower() in ("true", "1", "yes"),
            "label": meta["label"],
            "description": meta["description"],
        }
    from app import entitlement
    import os
    # Admin tools that are stripped from shipped editions; hide their tabs when
    # the code is absent. Where the code is still present (e.g. a dev bind-mount
    # feeding a client instance), a deployment can force the developer/QA tools
    # off with OCR_DEV_TOOLS=0 so a client admin panel never surfaces them.
    # Unset preserves the code-presence behavior for dev and normal installs.
    dev_tools = os.environ.get("OCR_DEV_TOOLS", "1").strip().lower() in ("1", "true", "yes")
    return {
        "modules": modules,
        # Runtime module-toggle UI (the Modules settings tab) is a dev-only
        # affordance; editions determine modules by build+entitlement, not a
        # runtime switch. Gated on the same OCR_DEV_TOOLS flag.
        "dev_tools": dev_tools,
        "exercise_tester": dev_tools and importlib.util.find_spec("app.routers.exercise_tester") is not None,
        "stress_tester": dev_tools and importlib.util.find_spec("app.services.stress_report") is not None,
        # Exercise authoring (Exercise Studio + custom "Upload Exercise") is
        # not release-hardened yet, so it is a dev-only surface: gated on
        # OCR_DEV_TOOLS in addition to the studio router being present. Clients
        # and shipped editions never see it until it is tested.
        "exercise_authoring": dev_tools and importlib.util.find_spec("app.routers.studio") is not None,
    }
