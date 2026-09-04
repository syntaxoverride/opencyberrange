"""Shared fixtures for the backend smoke suite.

The environment is prepared BEFORE the app is imported so app.config picks
up test values instead of anything in a local .env file. Tests never touch
the live ocr-db: the engine URL comes from TEST_DATABASE_URL, an ephemeral
Postgres supplied by the verify phase or CI. When TEST_DATABASE_URL is
unset, every DB-backed fixture skips cleanly and only tests that stay off
the database (health, entitlement) run.
"""
import hashlib
import os
import uuid

import pytest

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")

# A syntactically valid but unreachable URL keeps module imports working when
# no test database is provided. SQLAlchemy connects lazily, so nothing dials
# this address unless a DB-backed test runs, and those skip instead.
_PLACEHOLDER_URL = (
    "postgresql://ocr_test:ocr_test@127.0.0.1:59999/ocr_test_placeholder"
)

# Real environment variables win over .env in pydantic-settings, so setting
# these here guarantees the app under test cannot pick up live credentials.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL or _PLACEHOLDER_URL
os.environ.setdefault("JWT_SECRET", "pytest-only-jwt-secret-do-not-deploy")
os.environ.setdefault("CORS_ORIGINS", "http://testserver")
# Point entitlement at a path that never exists unless a test overrides it,
# so a stray data/entitlement.json in the working tree cannot leak in.
os.environ.setdefault("OCR_ENTITLEMENT_FILE", "/nonexistent/pytest-entitlement.json")

from fastapi.testclient import TestClient  # noqa: E402

import app.main as main_module  # noqa: E402
from app import database  # noqa: E402
from app.auth import get_password_hash  # noqa: E402
from app.models import FlagAttempt, Lab, LabCompletion, User  # noqa: E402
from app.routers import auth as auth_router_module  # noqa: E402
from app.routers import curriculum as curriculum_module  # noqa: E402

app = main_module.app

# slowapi keeps per-IP counters in process memory. Every request in the suite
# arrives from the same test client address, so the login and flag limits
# would couple otherwise independent tests. Disable each module's limiter.
for _mod in (main_module, auth_router_module, curriculum_module):
    _limiter = getattr(_mod, "limiter", None)
    if _limiter is not None:
        _limiter.enabled = False

TEST_PASSWORD = "Correct#Horse7Battery"
TEST_FLAG = "OCR{pytest_smoke_flag}"


@pytest.fixture(scope="session")
def client():
    """TestClient WITHOUT the lifespan context.

    The lifespan block runs live-schema migrations, starts the scheduler,
    and probes Docker, none of which belong in unit tests. Skipping the
    context manager means lifespan never executes; the schema instead comes
    from create_all in db_schema.
    """
    return TestClient(app)


@pytest.fixture(scope="session")
def db_schema():
    """Create the ORM schema once in the ephemeral database, or skip."""
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL not set; DB-backed test skipped")
    database.Base.metadata.create_all(bind=database.engine)
    yield
    database.engine.dispose()


@pytest.fixture()
def db_session(db_schema):
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def test_password():
    return TEST_PASSWORD


@pytest.fixture()
def test_flag():
    return TEST_FLAG


@pytest.fixture()
def test_user(db_session):
    """A fresh approved, active student per test. Unique name keeps tests
    independent even when a prior run left rows behind."""
    suffix = uuid.uuid4().hex[:10]
    user = User(
        username=f"pytest_{suffix}",
        email=f"pytest_{suffix}@university.edu",
        hashed_password=get_password_hash(TEST_PASSWORD),
        is_active=True,
        is_admin=False,
        role="student",
        is_approved=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    yield user
    db_session.query(FlagAttempt).filter(FlagAttempt.user_id == user.id).delete()
    db_session.query(LabCompletion).filter(LabCompletion.user_id == user.id).delete()
    db_session.query(User).filter(User.id == user.id).delete()
    db_session.commit()


@pytest.fixture()
def test_lab(db_session):
    """A fresh public, active lab whose flag_hash matches TEST_FLAG."""
    suffix = uuid.uuid4().hex[:10]
    lab = Lab(
        name=f"Pytest Smoke Lab {suffix}",
        slug=f"pytest-smoke-{suffix}",
        description="Created by the automated test harness",
        compose_file="services: {}\n",
        is_active=True,
        visibility="public",
        flag_hash=hashlib.sha256(TEST_FLAG.encode()).hexdigest(),
    )
    db_session.add(lab)
    db_session.commit()
    db_session.refresh(lab)
    yield lab
    # Attempts and completions reference the lab, so clear them first.
    db_session.query(FlagAttempt).filter(FlagAttempt.lab_id == lab.id).delete()
    db_session.query(LabCompletion).filter(LabCompletion.lab_id == lab.id).delete()
    db_session.query(Lab).filter(Lab.id == lab.id).delete()
    db_session.commit()


@pytest.fixture()
def auth_headers(client, test_user):
    """Bearer headers for test_user obtained through the real login flow."""
    resp = client.post(
        "/api/auth/login",
        data={"username": test_user.username, "password": TEST_PASSWORD},
    )
    assert resp.status_code == 200, f"login failed in fixture: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
