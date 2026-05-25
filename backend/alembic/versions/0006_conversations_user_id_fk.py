"""add conversations.user_id FK to users"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_conversations_user_id_fk"
down_revision: str | Sequence[str] | None = "0005_add_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_conversations_user_id_created_at", table_name="conversations")
    op.drop_column("conversations", "user_id")
    op.add_column(
        "conversations",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "users.id", name="fk_conversations_user_id", ondelete="SET NULL"
            ),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_conversations_user_id_created_at",
        "conversations",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_conversations_user_id_created_at", table_name="conversations")
    op.drop_column("conversations", "user_id")
    op.add_column(
        "conversations",
        sa.Column("user_id", sa.String(), nullable=False, server_default=""),
    )
    op.create_index(
        "ix_conversations_user_id_created_at",
        "conversations",
        ["user_id", "created_at"],
    )
