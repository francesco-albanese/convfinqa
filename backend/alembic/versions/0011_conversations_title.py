"""conversations.title for auto-generated chat titles"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_conversations_title"
down_revision: str | Sequence[str] | None = "0010_documents_conv_questions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("title", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("conversations", "title")
