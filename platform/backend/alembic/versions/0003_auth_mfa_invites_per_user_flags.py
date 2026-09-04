"""Auth hardening tables: token revocation, MFA columns, invite codes, per-student flags.

Revision ID: 0003_auth_mfa_invites
Revises: 0002_wg_client_ip_unique
Create Date: 2026-07-19

Adds:
- revoked_tokens: DB-backed JWT revocation list keyed by jti
- users.totp_secret / users.mfa_enabled: TOTP MFA enrollment state
- invite_codes: invite-gated registration codes
- lab_sessions.seeded_flag_hash: hash of a per-student flag seeded into the
  session's containers, checked before the shared labs.flag_hash
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0003_auth_mfa_invites"
down_revision: Union[str, None] = "0002_wg_client_ip_unique"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "revoked_tokens",
        sa.Column("jti", sa.String(length=64), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "revoked_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_revoked_tokens_user", "revoked_tokens", ["user_id"])

    op.create_table(
        "invite_codes",
        sa.Column("code", sa.String(length=64), primary_key=True),
        sa.Column("email", sa.String(length=100), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("used_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
    )

    op.add_column(
        "users",
        sa.Column("totp_secret", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "mfa_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )

    op.add_column(
        "lab_sessions",
        sa.Column("seeded_flag_hash", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("lab_sessions", "seeded_flag_hash")
    op.drop_column("users", "mfa_enabled")
    op.drop_column("users", "totp_secret")
    op.drop_table("invite_codes")
    op.drop_index("ix_revoked_tokens_user", table_name="revoked_tokens")
    op.drop_table("revoked_tokens")
