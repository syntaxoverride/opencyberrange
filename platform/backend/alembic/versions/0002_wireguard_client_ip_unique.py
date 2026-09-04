"""Add UNIQUE constraint on wireguard_configs.client_ip.

Revision ID: 0002_wg_client_ip_unique
Revises: 0001_baseline
Create Date: 2026-07-19

The model has declared client_ip unique=True for a while, but databases built
before that declaration (or altered by hand) may lack the actual constraint,
which is what allowed the VPN IP allocator collision bug. Applying this
migration closes that hole at the database layer.

BEFORE applying to a database that has been serving VPN peers, check for and
resolve duplicate client_ip rows or the ALTER will fail:

    SELECT client_ip, COUNT(*) FROM wireguard_configs
    GROUP BY client_ip HAVING COUNT(*) > 1;
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa  # noqa: F401

# revision identifiers, used by Alembic.
revision: str = "0002_wg_client_ip_unique"
down_revision: Union[str, None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_wireguard_configs_client_ip",
        "wireguard_configs",
        ["client_ip"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_wireguard_configs_client_ip",
        "wireguard_configs",
        type_="unique",
    )
