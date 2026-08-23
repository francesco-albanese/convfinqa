"""add rate_limit scope key"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_rate_limit_scope"
down_revision: str | Sequence[str] | None = "0011_conversations_title"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SUSPICIOUS_ATTEMPT_SCOPE = "suspicious_attempt"


def upgrade() -> None:
    op.add_column(
        "rate_limit",
        sa.Column(
            "scope",
            sa.Text(),
            nullable=False,
            server_default=SUSPICIOUS_ATTEMPT_SCOPE,
        ),
    )
    op.alter_column("rate_limit", "scope", server_default=None)
    op.drop_constraint("pk_rate_limit", "rate_limit", type_="primary")
    op.create_primary_key(
        "pk_rate_limit", "rate_limit", ["scope", "user_id", "window_start"]
    )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM rate_limit WHERE scope <> :scope").bindparams(
            scope=SUSPICIOUS_ATTEMPT_SCOPE
        )
    )
    op.drop_constraint("pk_rate_limit", "rate_limit", type_="primary")
    op.create_primary_key("pk_rate_limit", "rate_limit", ["user_id", "window_start"])
    op.drop_column("rate_limit", "scope")
