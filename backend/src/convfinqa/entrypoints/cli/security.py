import asyncio
import os
import sys
import uuid
from typing import Annotated

import typer

from convfinqa.application.live_regression_campaign import (
    LiveCampaignConfig,
    LiveCampaignNotConfirmedError,
    LiveCampaignReport,
    LiveRegressionCampaignRunner,
    require_live_campaign_gate,
)
from convfinqa.config import Settings
from convfinqa.container import bootstrap_application

security_app = typer.Typer(no_args_is_help=True, add_completion=False)


@security_app.command(name="campaign")
def campaign(
    user_id: Annotated[
        str,
        typer.Option(
            "--user-id",
            help="UUID of an existing user row to own the throwaway fixture Conversations.",
        ),
    ],
    confirm: Annotated[
        bool,
        typer.Option(
            "--confirm",
            help="Explicit opt-in required alongside CONVFINQA_RUN_LIVE_SECURITY_CAMPAIGN=1.",
        ),
    ] = False,
    models: Annotated[
        str | None,
        typer.Option(
            "--models",
            help="Comma-separated model ids to run. Defaults to settings.llm_models.",
        ),
    ] = None,
    request_cap: Annotated[
        int,
        typer.Option(
            "--request-cap", help="Max live LLM calls across the whole campaign."
        ),
    ] = 30,
    token_cap: Annotated[
        int,
        typer.Option(
            "--token-cap",
            help="Max cumulative input+output tokens across the campaign.",
        ),
    ] = 6000,
    pace_seconds: Annotated[
        float,
        typer.Option("--pace-seconds", help="Serial delay between live calls."),
    ] = 2.0,
    max_output_tokens: Annotated[
        int,
        typer.Option(
            "--max-output-tokens",
            help="Per-call output token ceiling for the campaign.",
        ),
    ] = 200,
) -> None:
    """Run the opt-in live provider security regression campaign.

    Requires CONVFINQA_RUN_LIVE_SECURITY_CAMPAIGN=1 in the environment AND
    --confirm. Neither alone is enough, so this can never run as a side
    effect of a normal local or CI test invocation.
    """
    try:
        require_live_campaign_gate(env=os.environ, confirmed=confirm)
    except LiveCampaignNotConfirmedError as exc:
        sys.stdout.write(f"[refused] {exc}\n")
        raise typer.Exit(code=1) from exc

    base_settings = Settings()
    campaign_settings = base_settings.model_copy(
        update={"llm_max_output_tokens": max_output_tokens}
    )
    model_list = (
        tuple(model.strip() for model in models.split(",") if model.strip())
        if models
        else tuple(base_settings.llm_models)
    )
    config = LiveCampaignConfig(
        user_id=uuid.UUID(user_id),
        models=model_list,
        request_cap=request_cap,
        token_cap=token_cap,
        pace_seconds=pace_seconds,
    )

    container = bootstrap_application(campaign_settings)
    runner = LiveRegressionCampaignRunner(
        send_message=container.send_message,
        conversations=container.conversations,
        campaign_fixtures=container.campaign_fixtures,
        config=config,
    )
    try:
        report = asyncio.run(runner.run())
    finally:
        try:
            asyncio.run(container.engine.dispose())
        except Exception:  # noqa: BLE001
            pass

    _print_report(report)
    if not report.passed:
        raise typer.Exit(code=1)


def _print_report(report: LiveCampaignReport) -> None:
    for outcome in report.outcomes:
        sys.stdout.write(
            f"[{outcome.status.value.upper():7}] {outcome.category.value:11} "
            f"{outcome.case_id:35} model={outcome.model} — {outcome.detail}\n"
        )
    sys.stdout.write(
        f"\nrequests_made={report.requests_made} tokens_used={report.tokens_used} "
        f"stopped_early_reason={report.stopped_early_reason or 'none'}\n"
    )
    sys.stdout.write("PASS\n" if report.passed else "FAIL\n")
