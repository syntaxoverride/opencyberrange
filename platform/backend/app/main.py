"""
OpenCyberRange Platform - Main Application
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import os

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.database import engine, Base
# Runtime module contract: modules under app/modules/ wire themselves in by
# discovery. Register each present module's ORM models with Base.metadata now,
# before create_all() runs in the lifespan startup.
from app import modules as module_registry
module_registry.register_models()
from app.routers import auth, labs, admin, curriculum, courses, dashboard, setup, curriculum_admin, instructor
from app.routers import settings as settings_router
from app.routers import modules as modules_router
from app.routers import rangebox as rangebox_router
from app.services.scheduler import start_scheduler, shutdown_scheduler
from app.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rate limiter - uses IP address for identification
# Default: 100 requests per minute for authenticated endpoints
# Auth endpoints have stricter limits configured in their router
#
# Storage: RATELIMIT_STORAGE_URI picks the counter backend (any URI the
# `limits` library accepts, e.g. redis://host:6379 or memcached://host:11211).
# The default "memory://" keeps counters PER PROCESS, so with N uvicorn
# workers the effective limit is up to N times the configured value. Set a
# shared backend whenever the API runs multi-worker and strict limits matter.
# NOTE: several routers (auth.py, admin.py, settings.py, ...) build their own
# Limiter instances that stay on in-process memory until they read this same
# variable; until then their limits also multiply per worker.
_RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],
    storage_uri=_RATELIMIT_STORAGE_URI,
)

# Scheduler leader election. Every uvicorn worker runs the lifespan below, so
# without a guard each worker would start its own copy of the background
# scheduler and the cleanup jobs would race (double session teardown, etc.).
# A Postgres session-level advisory lock elects one leader: the same pattern
# must outlive any single transaction. The winning worker holds a dedicated
# connection for its whole life; when that process dies, Postgres releases the
# lock and the next restarted worker can win it.
_SCHEDULER_LEADER_LOCK_KEY = 7391002
_scheduler_leader_conn = None


def _try_acquire_scheduler_leadership() -> bool:
    """Return True when this worker should run the background scheduler.

    Grabs pg_try_advisory_lock on a connection detached from the pool and
    keeps it open for the process lifetime, which is what keeps the
    session-level lock held. Fails open (returns True) when the probe itself
    errors, because no scheduler at all is worse than a duplicated one.
    """
    global _scheduler_leader_conn
    from sqlalchemy import text
    try:
        conn = engine.connect()
    except Exception as e:
        logger.warning(
            "Scheduler leader election: connect failed (%s); "
            "running scheduler in this worker anyway", e)
        return True
    try:
        got = conn.execute(
            text("SELECT pg_try_advisory_lock(:k)"),
            {"k": _SCHEDULER_LEADER_LOCK_KEY},
        ).scalar()
    except Exception as e:
        conn.close()
        logger.warning(
            "Scheduler leader election: lock probe failed (%s); "
            "running scheduler in this worker anyway", e)
        return True
    if got:
        # Detach so the pool never recycles this connection (recycling would
        # silently drop the session lock) and pool capacity is not reduced.
        conn.detach()
        _scheduler_leader_conn = conn
        return True
    conn.close()
    return False


def _release_scheduler_leadership() -> None:
    """Close the detached leader connection, releasing the advisory lock."""
    global _scheduler_leader_conn
    if _scheduler_leader_conn is not None:
        try:
            _scheduler_leader_conn.close()
        except Exception:
            pass
        _scheduler_leader_conn = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting OpenCyberRange Platform...")

    # Wait for database to become available (handles Docker restart race condition
    # where backend starts before PostgreSQL is accepting connections)
    import asyncio as _asyncio
    from sqlalchemy.exc import OperationalError

    max_retries = 30
    retry_delay = 2  # seconds
    for attempt in range(1, max_retries + 1):
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Database schema initialized successfully.")
            break
        except OperationalError as e:
            if attempt == max_retries:
                logger.error(
                    "Could not connect to database after %d attempts (%ds). Giving up.",
                    max_retries, max_retries * retry_delay,
                )
                raise
            logger.warning(
                "Database not ready (attempt %d/%d): %s -- retrying in %ds...",
                attempt, max_retries, str(e).split('\n')[0], retry_delay,
            )
            await _asyncio.sleep(retry_delay)

    # Add missing columns to existing tables (safe idempotent migration)
    from sqlalchemy import text, inspect as sa_inspect
    with engine.connect() as conn:
        inspector = sa_inspect(engine)
        labs_columns = [c['name'] for c in inspector.get_columns('labs')]
        if 'is_course_exclusive' not in labs_columns:
            conn.execute(text("ALTER TABLE labs ADD COLUMN is_course_exclusive BOOLEAN DEFAULT FALSE"))
            conn.commit()
            logger.info("Added is_course_exclusive column to labs table")

        courses_columns = [c['name'] for c in inspector.get_columns('courses')]
        if 'is_archived' not in courses_columns:
            conn.execute(text("ALTER TABLE courses ADD COLUMN is_archived BOOLEAN DEFAULT FALSE"))
            conn.commit()
            logger.info("Added is_archived column to courses table")

        # Widen wireguard_configs.private_key for Fernet-encrypted keys (~128 chars)
        if 'wireguard_configs' in inspector.get_table_names():
            wg_columns = {c['name']: c for c in inspector.get_columns('wireguard_configs')}
            if 'private_key' in wg_columns:
                col_type = str(wg_columns['private_key']['type'])
                # Check if column is still VARCHAR(100) and needs widening
                if '100' in col_type:
                    conn.execute(text("ALTER TABLE wireguard_configs ALTER COLUMN private_key TYPE VARCHAR(256)"))
                    conn.commit()
                    logger.info("Widened wireguard_configs.private_key to VARCHAR(256)")

        if 'is_course_available' not in labs_columns:
            conn.execute(text("ALTER TABLE labs ADD COLUMN is_course_available BOOLEAN DEFAULT FALSE"))
            # Backfill: labs already marked course-exclusive should also be course-available
            conn.execute(text("UPDATE labs SET is_course_available = TRUE WHERE is_course_exclusive = TRUE"))
            conn.commit()
            logger.info("Added is_course_available column to labs table")

        # --- Role-based access: add 'role' column to users ---
        users_columns = [c['name'] for c in inspector.get_columns('users')]
        if 'role' not in users_columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'student' NOT NULL"))
            conn.execute(text("UPDATE users SET role = 'admin' WHERE is_admin = TRUE"))
            conn.execute(text("UPDATE users SET role = 'student' WHERE is_admin = FALSE"))
            conn.commit()
            logger.info("Added role column to users table, migrated from is_admin")

        # --- Lab visibility lifecycle: add 'visibility' and 'created_by' to labs ---
        # Re-read labs columns after potential earlier migrations
        labs_columns = [c['name'] for c in inspector.get_columns('labs')]
        if 'visibility' not in labs_columns:
            conn.execute(text("ALTER TABLE labs ADD COLUMN visibility VARCHAR(20) DEFAULT 'public' NOT NULL"))
            conn.execute(text("ALTER TABLE labs ADD COLUMN created_by INTEGER REFERENCES users(id) ON DELETE SET NULL"))
            conn.execute(text("""
                UPDATE labs SET visibility = CASE
                    WHEN is_course_exclusive = TRUE AND is_course_available = TRUE THEN 'course'
                    WHEN is_course_exclusive = TRUE AND is_course_available = FALSE THEN 'draft'
                    ELSE 'public'
                END
            """))
            conn.commit()
            logger.info("Added visibility/created_by columns to labs table, migrated from boolean flags")

        # --- Workbook deep-link: add 'workbook' column to labs ---
        labs_columns = [c['name'] for c in inspector.get_columns('labs')]
        if 'workbook' not in labs_columns:
            conn.execute(text("ALTER TABLE labs ADD COLUMN workbook VARCHAR(255)"))
            conn.commit()
            logger.info("Added workbook column to labs table")

        # --- Week number: add 'week' column to labs for auto-assignment grouping ---
        labs_columns = [c['name'] for c in inspector.get_columns('labs')]
        if 'week' not in labs_columns:
            conn.execute(text("ALTER TABLE labs ADD COLUMN week INTEGER"))
            conn.commit()
            logger.info("Added week column to labs table")

        # --- Shared-VM dependency: add 'requires_kvm' column to labs ---
        labs_columns = [c['name'] for c in inspector.get_columns('labs')]
        if 'requires_kvm' not in labs_columns:
            conn.execute(text("ALTER TABLE labs ADD COLUMN requires_kvm BOOLEAN DEFAULT FALSE"))
            conn.commit()
            logger.info("Added requires_kvm column to labs table")

        # --- ws_tickets: single-use WebSocket auth tickets (RangeBox VNC etc.) ---
        # Used by auth.py via raw SQL; there is no ORM model, so create it here
        # so fresh installs have it (previously hand-created only on the dev host).
        if 'ws_tickets' not in inspector.get_table_names():
            conn.execute(text(
                "CREATE TABLE IF NOT EXISTS ws_tickets ("
                " ticket VARCHAR(64) PRIMARY KEY,"
                " user_id INTEGER NOT NULL,"
                " expires_at TIMESTAMP NOT NULL)"))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_ws_tickets_expires ON ws_tickets (expires_at)"))
            conn.commit()
            logger.info("Created ws_tickets table")

        # --- Track sequential gating: add 'sequential' column to tracks ---
        tracks_columns = [c['name'] for c in inspector.get_columns('tracks')]
        if 'sequential' not in tracks_columns:
            conn.execute(text("ALTER TABLE tracks ADD COLUMN sequential BOOLEAN DEFAULT TRUE NOT NULL"))
            conn.commit()
            logger.info("Added sequential column to tracks table")

        # --- RangeBox: add 'rangebox_enabled' column to lab_sessions ---
        lab_sessions_columns = [c['name'] for c in inspector.get_columns('lab_sessions')]
        if 'rangebox_enabled' not in lab_sessions_columns:
            conn.execute(text("ALTER TABLE lab_sessions ADD COLUMN rangebox_enabled BOOLEAN DEFAULT FALSE"))
            conn.commit()
            logger.info("Added rangebox_enabled column to lab_sessions table")

        # --- Assignment start_date: add 'start_date' column to assignments ---
        if 'assignments' in inspector.get_table_names():
            asn_columns = [c['name'] for c in inspector.get_columns('assignments')]
            if 'start_date' not in asn_columns:
                conn.execute(text("ALTER TABLE assignments ADD COLUMN start_date TIMESTAMP"))
                conn.commit()
                logger.info("Added start_date column to assignments table")

        # --- Course lab display_name: add 'display_name' column to course_lab_assignments ---
        if 'course_lab_assignments' in inspector.get_table_names():
            cla_columns = [c['name'] for c in inspector.get_columns('course_lab_assignments')]
            if 'display_name' not in cla_columns:
                conn.execute(text("ALTER TABLE course_lab_assignments ADD COLUMN display_name VARCHAR(255)"))
                conn.commit()
                logger.info("Added display_name column to course_lab_assignments table")

        # --- SOC Deliverables Workspace: new columns ---


        # --- Shared VM lifecycle tables ---

    # Seed default platform settings
    from app.services.settings_service import seed_defaults
    from app.database import SessionLocal
    settings_db = SessionLocal()
    try:
        seed_defaults(settings_db)
    finally:
        settings_db.close()

    # Enable each optional module this tier's entitlement grants, so the runtime
    # gate (module_access_control middleware) unlocks without a manual toggle.
    # entitlement.modules is written by the release pipeline from the tier's
    # module list (e.g. ["soc"] on a SOC tier); base tiers have none.
    from app import entitlement as _ent
    from app.services import settings_service as _mod_ss
    mod_db = SessionLocal()
    try:
        # Seed the entitlement's modules as the first-run DEFAULT only. Entitlement
        # decides what a tier MAY enable; once the operator has completed setup,
        # their choice (setup wizard or Admin Settings > Modules) is authoritative
        # and must not be re-forced on every boot -- otherwise disabling a module
        # never sticks. Before setup, seed the default so the module works
        # out of the box on the entitled tier.
        _setup_done = (_mod_ss.get_setting(mod_db, "setup_complete", "false") or "").lower() in ("true", "1", "yes")
        if not _setup_done:
            for _m in _ent.modules():
                _key = f"module_{_m}_enabled"
                if (_mod_ss.get_setting(mod_db, _key, "false") or "").lower() not in ("true", "1", "yes"):
                    _mod_ss.set_setting(mod_db, _key, "true")
                    logger.info("Enabled module '%s' from entitlement (first-run default)", _m)
    except Exception as e:
        logger.warning(f"Module enable seeding: {e}")
    finally:
        mod_db.close()

    # (SOC team-game scenario auto-discover and stuck-exercise recovery removed
    # with the team-game module.)

    # Auto-apply firewall rules on startup so the server is secure after reboot
    # (same rules the admin "Fix Rules" button applies, but automatic)
    try:
        import requests as req_lib
        from app.config import settings
        from app.services.docker_manager import DockerManager
        _dm = DockerManager()

        applied = []
        # 1. Peer Manager VPN rules
        try:
            api_url = settings.WG_API_URL
            headers = {}
            if settings.WG_API_KEY:
                headers["X-API-Key"] = settings.WG_API_KEY
            resp = req_lib.post(f"{api_url}/firewall/ensure", headers=headers, timeout=10)
            if resp.status_code == 200:
                applied.extend(resp.json().get("rules", []))
        except Exception as fw_e:
            logger.warning(f"Startup firewall -- Peer Manager: {fw_e}")

        # 2. Lab network isolation (outbound: lab→host LAN)
        applied.extend(_dm.ensure_lab_network_isolation())

        # 3. Inbound isolation (external interfaces → Docker lab networks)
        applied.extend(_dm.ensure_inbound_isolation())

        if applied:
            logger.info("Startup firewall: applied %d rules", len(applied))
        else:
            logger.info("Startup firewall: all rules already in place")
    except Exception as e:
        logger.warning(f"Startup firewall auto-apply: {e}")

    # Only the advisory-lock leader runs the scheduler; the other workers
    # serve requests but skip the background cleanup loops.
    scheduler_started = _try_acquire_scheduler_leadership()
    if scheduler_started:
        logger.info("Scheduler leader lock acquired (pid %d); starting background scheduler", os.getpid())
        start_scheduler()
    else:
        logger.info("Scheduler leader lock held by another worker (pid %d); skipping scheduler", os.getpid())
    yield
    # Shutdown
    logger.info("Shutting down...")
    if scheduler_started:
        shutdown_scheduler()
    _release_scheduler_leadership()


app = FastAPI(
    title="OpenCyberRange",
    description="Cybersecurity Training Platform",
    version="2.0.0",
    lifespan=lifespan,
)

# Attach rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware - configurable via CORS_ORIGINS environment variable
# In production, set CORS_ORIGINS to your domain(s)
cors_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Default off: enable_api_docs has no DB row on a fresh install and
# get_setting falls back to "false", so an internet-facing deploy hides the
# API docs until an admin flips the setting (or ENABLE_API_DOCS=true is set).
_DOCS_PATHS = {"/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect"}


@app.middleware("http")
async def docs_access_control(request: Request, call_next):
    """Gate /docs, /redoc, /openapi.json behind the enable_api_docs setting."""
    if request.url.path in _DOCS_PATHS:
        # Env var override for emergency debugging without a running DB
        if os.environ.get("ENABLE_API_DOCS", "").lower() in ("1", "true", "yes"):
            return await call_next(request)
        # Otherwise check the DB setting (cached in memory after first load)
        from app.database import SessionLocal
        from app.services import settings_service
        db = SessionLocal()
        try:
            enabled = settings_service.get_setting(db, "enable_api_docs", "false")
        finally:
            db.close()
        if enabled.lower() not in ("true", "1", "yes"):
            return JSONResponse(status_code=404, content={"detail": "Not Found"})
    return await call_next(request)


# {prefix: setting_key} built from the discovered modules' manifests. A new
# module declaring gate_prefixes is enforced here with no edit to this file.
_MODULE_GATE = module_registry.gate_map()


@app.middleware("http")
async def module_access_control(request: Request, call_next):
    """Return 404 for disabled module API paths (hot-toggle without restart)."""
    path = request.url.path
    for prefix, setting_key in _MODULE_GATE.items():
        if path.startswith(prefix):
            from app.database import SessionLocal
            from app.services import settings_service
            db = SessionLocal()
            try:
                enabled = settings_service.get_setting(db, setting_key, "false")
            finally:
                db.close()
            if enabled.lower() not in ("true", "1", "yes"):
                return JSONResponse(
                    status_code=404,
                    content={"detail": "Module is not enabled"},
                )
            break
    return await call_next(request)


# ─── Impersonation read-only middleware ───────────────────────────
# Blocks all mutating requests (POST/PUT/DELETE/PATCH) when the JWT
# carries imp=True, with a small whitelist for safe operations.
_IMPERSONATION_ALLOWED_PATHS = {
    "/api/auth/impersonate/exit",  # Must be able to exit
    "/api/auth/change-password",   # Blocked by own logic, but whitelist avoids double-error
}

@app.middleware("http")
async def impersonation_read_only_middleware(request: Request, call_next):
    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        path = request.url.path
        if path not in _IMPERSONATION_ALLOWED_PATHS:
            auth_header = request.headers.get("authorization", "")
            if auth_header.startswith("Bearer "):
                token_str = auth_header[7:]
                try:
                    from jose import jwt as _jwt
                    payload = _jwt.decode(
                        token_str, settings.JWT_SECRET,
                        algorithms=[settings.JWT_ALGORITHM],
                    )
                    if payload.get("imp"):
                        return JSONResponse(
                            status_code=403,
                            content={
                                "detail": "Action blocked: you are viewing as another user",
                                "impersonating": True,
                            },
                            headers={"X-Impersonating": "true"},
                        )
                except Exception:
                    pass  # Let downstream auth handle invalid tokens
    return await call_next(request)


# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(labs.router, prefix="/api/labs", tags=["Labs"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(curriculum.router, prefix="/api/exercises", tags=["Exercises"])
app.include_router(courses.router, prefix="/api/courses", tags=["Courses"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(settings_router.router, prefix="/api/settings", tags=["Settings"])
app.include_router(setup.router, prefix="/api/setup", tags=["Setup"])
app.include_router(curriculum_admin.router, prefix="/api/admin/curriculum", tags=["Curriculum Admin"])
app.include_router(instructor.router, prefix="/api/instructor", tags=["Instructor"])
app.include_router(modules_router.router, prefix="/api/modules", tags=["Modules"])
app.include_router(rangebox_router.router, prefix="/api/rangebox", tags=["RangeBox"])

# Optional module routers, discovered from app/modules/. Mounted AFTER the core
# routers so a module that extends a shared prefix (e.g. the exercise tester on
# /api/admin) layers on top. Present in dev; stripped per-edition by the build
# registry. Adding a module here requires no edit to this file.
module_registry.mount_routers(app)


@app.get("/")
async def root():
    return {"message": "OpenCyberRange API", "version": "2.0.0"}


@app.get("/health")
def health():
    """Health probe with a real database check.

    Sync def on purpose: FastAPI runs it in the threadpool, so the blocking
    SELECT never stalls the event loop. Returns 200/healthy when the DB
    answers, 503/degraded when it does not, so load balancers and container
    healthchecks see actual readiness instead of a static string.
    """
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        logger.warning("Health check: database probe failed: %s", str(e).split("\n")[0])
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "database": "down"},
        )
    return {"status": "healthy", "database": "up"}
