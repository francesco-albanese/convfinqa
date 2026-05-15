from unittest.mock import MagicMock, call, patch

import pytest

from convfinqa.adapters.persistence.sqlalchemy.engine import create_engine


@pytest.mark.unit
def test_engine_pool_config_for_aurora_pause() -> None:
    with patch(
        "convfinqa.adapters.persistence.sqlalchemy.engine.create_async_engine"
    ) as mock_create:
        mock_create.return_value = MagicMock()
        create_engine("postgresql+asyncpg://user:pass@localhost/db")

    assert mock_create.call_args == call(
        "postgresql+asyncpg://user:pass@localhost/db",
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=2,
        max_overflow=2,
        future=True,
    )
