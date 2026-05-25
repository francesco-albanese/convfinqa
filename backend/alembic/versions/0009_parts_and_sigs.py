"""add messages.parts and messages.reasoning_signatures columns"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009_parts_and_sigs"
down_revision: str | Sequence[str] | None = "0008_enable_pg_cron"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column("parts", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "messages",
        sa.Column("reasoning_signatures", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("messages", "reasoning_signatures")
    op.drop_column("messages", "parts")
