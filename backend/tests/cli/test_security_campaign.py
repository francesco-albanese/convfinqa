from typer.testing import CliRunner

from convfinqa.entrypoints.cli.app import app

runner = CliRunner()

DUMMY_USER_ID = "00000000-0000-0000-0000-000000000001"


def test_campaign_refuses_without_env_gate() -> None:
    result = runner.invoke(
        app,
        ["security", "campaign", "--user-id", DUMMY_USER_ID, "--confirm"],
        env={"CONVFINQA_RUN_LIVE_SECURITY_CAMPAIGN": ""},
    )

    assert result.exit_code == 1
    assert "refused" in result.output.casefold()


def test_campaign_refuses_without_explicit_confirm_flag() -> None:
    result = runner.invoke(
        app,
        ["security", "campaign", "--user-id", DUMMY_USER_ID],
        env={"CONVFINQA_RUN_LIVE_SECURITY_CAMPAIGN": "1"},
    )

    assert result.exit_code == 1
    assert "refused" in result.output.casefold()
