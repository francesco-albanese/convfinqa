from typer.testing import CliRunner

from convfinqa.entrypoints.cli.app import app

runner = CliRunner()


def test_chat_help_lists_documented_options() -> None:
    result = runner.invoke(app, ["chat", "--help"])

    assert result.exit_code == 0
    assert "--user-id" in result.output
    assert "--base-url" in result.output
