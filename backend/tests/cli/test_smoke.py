import click
from typer.testing import CliRunner

from convfinqa.entrypoints.cli.app import app

runner = CliRunner()


def test_chat_help_lists_documented_options() -> None:
    result = runner.invoke(app, ["chat", "--help"], terminal_width=120)
    output = click.unstyle(result.output)

    assert result.exit_code == 0
    assert "--user-id" in output
    assert "--base-url" in output
