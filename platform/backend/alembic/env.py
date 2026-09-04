"""Alembic environment for the OCR backend.

Wires Alembic to the app's own SQLAlchemy Base and to DATABASE_URL, the same
environment variable the application reads. All model modules that register
tables on Base.metadata are imported here so autogenerate sees the full schema.
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Make the backend package importable when alembic is invoked from
# platform/backend (prepend_sys_path covers the normal case; keep this as a
# belt-and-suspenders for invocations from other working directories).
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        url = (config.get_main_option("sqlalchemy.url") or "").strip()
    return url


DB_URL = _database_url()

# app.database builds its engine from settings.DATABASE_URL at import time, so
# a placeholder keeps model imports working for offline (--sql) runs where no
# real URL is exported. create_engine never connects at import.
os.environ.setdefault(
    "DATABASE_URL", DB_URL or "postgresql://alembic:offline@localhost:5432/placeholder"
)

# app.config validates JWT_SECRET at import time as well. Migrations never use
# JWT, so satisfy the check with a throwaway random value when none is set.
if not os.environ.get("JWT_SECRET"):
    import secrets

    os.environ["JWT_SECRET"] = secrets.token_urlsafe(64)

from app.database import Base  # noqa: E402

# Import every module that defines Base models so metadata is complete.
import app.models  # noqa: F401,E402

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode: emit SQL to stdout, no DB needed."""
    url = DB_URL
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Export it before running alembic, "
            "for example: DATABASE_URL=postgresql://user:pass@host/db alembic upgrade --sql head"
        )
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode against DATABASE_URL."""
    if not DB_URL:
        raise RuntimeError(
            "DATABASE_URL is not set. Export it before running alembic, "
            "for example: DATABASE_URL=postgresql://user:pass@host/db alembic upgrade head"
        )
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = DB_URL
    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
