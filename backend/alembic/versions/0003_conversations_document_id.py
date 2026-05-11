"""conversations.document_id NOT NULL FK to documents

WHY NOT NULL with no backfill: the conversations table is empty in every
environment (no users yet). Once data exists a future migration would need
to add the column nullable, backfill, then alter to NOT NULL.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_conversations_document_id"
down_revision: str | Sequence[str] | None = "0002_documents_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column(
            "document_id",
            sa.Text(),
            sa.ForeignKey("documents.id", name="fk_conversations_document_id"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_conversations_document_id",
        "conversations",
        ["document_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_conversations_document_id", table_name="conversations")
    op.drop_constraint(
        "fk_conversations_document_id", "conversations", type_="foreignkey"
    )
    op.drop_column("conversations", "document_id")
