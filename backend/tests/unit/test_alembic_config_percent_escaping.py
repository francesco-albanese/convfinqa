from pathlib import Path

from alembic.config import Config as AlembicConfig

from tests.conftest import escape_configparser_percent

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_escape_configparser_percent_is_a_no_op_for_plain_paths() -> None:
    assert escape_configparser_percent("/home/user/convfinqa") == (
        "/home/user/convfinqa"
    )


def test_escape_configparser_percent_doubles_literal_percent_signs() -> None:
    assert escape_configparser_percent("/tmp/some%2Fworktree") == (
        "/tmp/some%%2Fworktree"
    )


def test_alembic_config_accepts_a_percent_encoded_path_when_escaped() -> None:
    config = AlembicConfig(str(PROJECT_ROOT / "alembic.ini"))
    path = "/tmp/some%2Fworktree/backend/alembic"

    config.set_main_option("script_location", escape_configparser_percent(path))

    assert config.get_main_option("script_location") == path
