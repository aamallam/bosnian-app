"""Single-use nonces for Apple and Google sign-in (POST /v1/auth/nonce).

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-06 07:21:29.136594
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "identity_nonces",
        sa.Column("nonce_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("nonce_hash", name=op.f("pk_identity_nonces")),
    )
    with op.batch_alter_table("identity_nonces", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_identity_nonces_expires_at"), ["expires_at"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("identity_nonces", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_identity_nonces_expires_at"))

    op.drop_table("identity_nonces")
