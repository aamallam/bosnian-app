"""Index for a learner's own attempts in a pair (GET /pairs/{id}/attempts).

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-05 23:20:19.787607
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("pairing_attempts", schema=None) as batch_op:
        batch_op.create_index(
            "ix_pairing_attempts_pair_learner",
            ["pair_id", "learner_id", "created_at"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("pairing_attempts", schema=None) as batch_op:
        batch_op.drop_index("ix_pairing_attempts_pair_learner")
