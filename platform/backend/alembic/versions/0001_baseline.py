"""Baseline: pre-Alembic schema marker.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-07-19

The platform predates Alembic; every table so far was created through
Base.metadata.create_all plus manual ALTER TABLE statements. Rather than
replay hundreds of CREATE TABLE operations, this revision is an empty stamp
point that represents that pre-existing schema.

Existing databases: mark them as being at this baseline WITHOUT running DDL:

    alembic stamp 0001_baseline

Fresh databases: create the schema through the app's normal startup
(Base.metadata.create_all), then stamp this baseline the same way. After
stamping, apply later revisions with alembic upgrade head.
"""
from typing import Sequence, Union

from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401

# revision identifiers, used by Alembic.
revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Intentionally empty: the schema this revision represents already exists
    # (or is created by Base.metadata.create_all on first boot).
    pass


def downgrade() -> None:
    pass
