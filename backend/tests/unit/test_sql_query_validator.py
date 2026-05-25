import pytest

from convfinqa.application.agent.sql.validator import validate_select


def test_valid_select_passes() -> None:
    validate_select("SELECT value_num FROM cells WHERE row_label='x' AND col_label='y'")


def test_multi_statement_rejected() -> None:
    with pytest.raises(ValueError, match="single SELECT"):
        validate_select("SELECT 1; SELECT 2")


def test_drop_table_rejected() -> None:
    with pytest.raises(ValueError, match="forbidden|only SELECT"):
        validate_select("DROP TABLE cells")


def test_attach_database_rejected() -> None:
    with pytest.raises(ValueError, match="forbidden|only SELECT"):
        validate_select("ATTACH DATABASE ':memory:' AS other")


def test_pragma_rejected() -> None:
    with pytest.raises(ValueError, match="forbidden|only SELECT"):
        validate_select("PRAGMA table_info(cells)")


def test_insert_rejected() -> None:
    with pytest.raises(ValueError, match="forbidden|only SELECT"):
        validate_select("INSERT INTO cells (row_label) VALUES ('x')")


def test_update_rejected() -> None:
    with pytest.raises(ValueError, match="forbidden|only SELECT"):
        validate_select("UPDATE cells SET value_num=1")


def test_delete_rejected() -> None:
    with pytest.raises(ValueError, match="forbidden|only SELECT"):
        validate_select("DELETE FROM cells")


def test_alter_table_rejected() -> None:
    with pytest.raises(ValueError, match="forbidden|only SELECT"):
        validate_select("ALTER TABLE cells ADD COLUMN extra TEXT")


def test_create_table_rejected() -> None:
    with pytest.raises(ValueError, match="forbidden|only SELECT"):
        validate_select("CREATE TABLE foo (id INTEGER)")


def test_begin_rejected() -> None:
    with pytest.raises(ValueError, match="forbidden|only SELECT"):
        validate_select("BEGIN")


def test_commit_rejected() -> None:
    with pytest.raises(ValueError, match="forbidden|only SELECT"):
        validate_select("COMMIT")
