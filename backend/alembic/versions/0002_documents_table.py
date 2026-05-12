"""documents table with generated tsvector and FTS indexes"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_documents_table"
down_revision: str | Sequence[str] | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SEARCH_TSV_EXPRESSION = (
    "to_tsvector('english', "
    "coalesce(title,'') || ' ' || "
    "coalesce(ticker,'') || ' ' || "
    "coalesce(pre_text,''))"
)


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("ticker", sa.Text(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("page", sa.Integer(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("pre_text", sa.Text(), nullable=True),
        sa.Column("post_text", sa.Text(), nullable=True),
        sa.Column("table_data", postgresql.JSONB(), nullable=True),
        sa.Column(
            "search_tsv",
            postgresql.TSVECTOR(),
            sa.Computed(SEARCH_TSV_EXPRESSION, persisted=True),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_documents_search_tsv",
        "documents",
        ["search_tsv"],
        postgresql_using="gin",
    )
    op.create_index("ix_documents_year", "documents", ["year"])
    op.create_index("ix_documents_ticker_year", "documents", ["ticker", "year"])


def downgrade() -> None:
    op.drop_index("ix_documents_ticker_year", table_name="documents")
    op.drop_index("ix_documents_year", table_name="documents")
    op.drop_index("ix_documents_search_tsv", table_name="documents")
    op.drop_table("documents")
