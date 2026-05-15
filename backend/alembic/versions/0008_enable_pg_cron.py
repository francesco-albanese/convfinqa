"""enable pg_cron extension and schedule TTL sweeps"""

from collections.abc import Sequence

from alembic import op

revision: str = "0008_enable_pg_cron"
down_revision: str | Sequence[str] | None = "0007_cache_ratelimit_idempotency"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_UPGRADE_SQL = """\
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'pg_cron') THEN
    CREATE EXTENSION IF NOT EXISTS pg_cron;
    PERFORM cron.schedule(
      'rate-limit-sweep',
      '0 3 * * *',
      'DELETE FROM rate_limit WHERE expires_at < now()'
    );
    PERFORM cron.schedule(
      'output-cache-sweep',
      '0 3 * * *',
      'DELETE FROM output_cache WHERE expires_at < now()'
    );
  END IF;
END;
$$;
"""

_DOWNGRADE_SQL = """\
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron') THEN
    PERFORM cron.unschedule('rate-limit-sweep');
    PERFORM cron.unschedule('output-cache-sweep');
    DROP EXTENSION pg_cron;
  END IF;
END;
$$;
"""


def upgrade() -> None:
    op.execute(_UPGRADE_SQL)


def downgrade() -> None:
    op.execute(_DOWNGRADE_SQL)
