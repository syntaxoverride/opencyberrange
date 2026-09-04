"""
Runtime module contract (the plugin loader).

A *module* is a subpackage of ``app.modules`` that exposes a module-level
``MANIFEST`` of type :class:`ModuleManifest`. On boot the core auto-discovers
every manifest and wires in its routers, API gate, scheduler ticks, and ORM
models. Adding or removing a module therefore never edits ``main.py``,
``scheduler.py``, or ``routers/modules.py``:

    add a module     = drop app/modules/<name>/  (+ an editions.yaml line for
                       entitlement modules so the build ships it)
    remove a module  = delete the directory (or let the build strip it)

Two kinds of manifest:
  * ``kind="module"``  -- an entitlement feature (SOC, and later liverange):
    has a ``setting_key`` + ``gate_prefixes`` and is reported to the setup
    wizard / sidebar via ``available_modules``.
  * ``kind="devtool"`` -- a developer/QA surface (Exercise Studio, the exercise
    tester, workbook upload): shipped only in dev builds, no entitlement gate.

A manifest holds *strings* (import paths), so importing it never drags in the
module's code -- presence is decided lazily by :func:`_present` via
``requires``. That keeps a build that stripped a module's files from crashing on
a stale manifest.
"""

from dataclasses import dataclass, field
import importlib
import importlib.util
import logging
import pkgutil

logger = logging.getLogger(__name__)


@dataclass
class RouterSpec:
    """One APIRouter to mount, and where."""
    import_path: str                 # e.g. "app.routers.soc_hunt"
    mounts: list                     # [(prefix, tag), ...]
    attr: str = "router"             # attribute on the module holding the APIRouter


@dataclass
class ModuleManifest:
    name: str                                            # "soc"
    label: str                                           # "SOC"
    description: str
    requires: str                                        # import path proving the code shipped
    kind: str = "module"                                 # "module" | "devtool"
    setting_key: str = ""                                # e.g. "module_x_enabled"
    gate_prefixes: list = field(default_factory=list)    # ["/api/x/"]
    routers: list = field(default_factory=list)          # [RouterSpec, ...]
    scheduler_ticks: list = field(default_factory=list)  # ["app.services.x_engine:tick"]
    models: list = field(default_factory=list)           # ["app.models_soc", ...]


# --- discovery ------------------------------------------------------------

_MANIFESTS_CACHE = None


def _iter_manifests():
    """Import every ``app.modules.<name>`` subpackage and yield its MANIFEST.

    A broken or partially-stripped manifest is logged and skipped, never fatal.
    """
    for info in pkgutil.iter_modules(__path__):
        if not info.ispkg:
            continue
        try:
            mod = importlib.import_module(f"{__name__}.{info.name}")
        except Exception as e:  # noqa: BLE001 -- a bad manifest must not kill boot
            logger.warning("modules: could not import manifest %r: %s", info.name, e)
            continue
        manifest = getattr(mod, "MANIFEST", None)
        if isinstance(manifest, ModuleManifest):
            yield manifest


def _present(manifest: ModuleManifest) -> bool:
    """True only if the module's code actually ships in this build."""
    if not manifest.requires:
        return True
    try:
        return importlib.util.find_spec(manifest.requires) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def discover(present_only: bool = True):
    """All manifests (cached). ``present_only`` filters to modules whose code ships."""
    global _MANIFESTS_CACHE
    if _MANIFESTS_CACHE is None:
        _MANIFESTS_CACHE = list(_iter_manifests())
    if present_only:
        return [m for m in _MANIFESTS_CACHE if _present(m)]
    return list(_MANIFESTS_CACHE)


# --- wiring points the core calls (the three discovery points) ------------

def register_models():
    """Import each present module's ORM model modules so their tables register
    with ``Base.metadata`` before ``create_all()``. Call at import time of main."""
    for m in discover():
        for path in m.models:
            try:
                importlib.import_module(path)
            except ImportError:
                logger.warning("modules[%s]: model module %r not importable", m.name, path)


def mount_routers(app) -> None:
    """Include each present module's routers. Call *after* the core routers so a
    module that extends a shared prefix (e.g. /api/admin) layers on top of it."""
    for m in discover():
        mounted = False
        for spec in m.routers:
            try:
                rmod = importlib.import_module(spec.import_path)
            except ImportError:
                continue  # file stripped in this edition
            router = getattr(rmod, spec.attr)
            for prefix, tag in spec.mounts:
                app.include_router(router, prefix=prefix, tags=[tag])
            mounted = True
        if mounted:
            logger.info("modules: mounted %s (%s)", m.name, m.kind)


def gate_map() -> dict:
    """``{prefix: setting_key}`` for the module access-control middleware."""
    gm = {}
    for m in discover():
        for prefix in m.gate_prefixes:
            gm[prefix] = m.setting_key
    return gm


def scheduler_ticks():
    """``[(label, async_callable), ...]`` background ticks from present modules."""
    ticks = []
    for m in discover():
        for spec in m.scheduler_ticks:
            mod_path, _, attr = spec.partition(":")
            try:
                tmod = importlib.import_module(mod_path)
            except ImportError:
                continue
            fn = getattr(tmod, attr, None)
            if fn is not None:
                ticks.append((f"{m.name}:{attr}", fn))
    return ticks


def known_modules() -> dict:
    """Entitlement modules (kind='module') as the legacy KNOWN_MODULES shape."""
    return {
        m.name: {
            "setting_key": m.setting_key,
            "label": m.label,
            "description": m.description,
            "requires": m.requires,
        }
        for m in discover(present_only=False)
        if m.kind == "module"
    }
