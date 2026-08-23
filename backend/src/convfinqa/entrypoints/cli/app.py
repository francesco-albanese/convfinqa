import asyncio
import json
import os
import sys
from typing import Annotated, cast

import httpx
import typer

from convfinqa.entrypoints.cli.eval import eval_app
from convfinqa.entrypoints.cli.prompts import prompts_app
from convfinqa.entrypoints.cli.security import security_app

app = typer.Typer(no_args_is_help=True, add_completion=False)
app.add_typer(prompts_app, name="prompts")
app.add_typer(eval_app, name="eval")
app.add_typer(security_app, name="security")

CLI_HTTP_TIMEOUT = httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0)


@app.callback()
def main(ctx: typer.Context) -> None:
    """convfinqa CLI."""
    del ctx


def _default_user_id() -> str:
    return os.getenv("USER", "dev-user")


@app.command(name="chat")
def chat(
    user_id: Annotated[
        str,
        typer.Option(
            "--user-id",
            help="User identity sent as X-User-Id header (defaults to $USER or 'dev-user').",
        ),
    ] = "",
    base_url: Annotated[
        str,
        typer.Option("--base-url", help="Base URL of the convfinqa API."),
    ] = "http://localhost:8000",
    document_id: Annotated[
        str,
        typer.Option(
            "--document-id",
            help="Document id to pin for new conversations.",
        ),
    ] = "",
) -> None:
    try:
        asyncio.run(
            _repl(
                user_id=user_id or _default_user_id(),
                base_url=base_url,
                document_id=document_id or None,
            )
        )
    except KeyboardInterrupt:
        sys.stdout.write("\n")


async def _repl(*, user_id: str, base_url: str, document_id: str | None) -> None:
    conversation_id: str | None = None
    async with httpx.AsyncClient(base_url=base_url, timeout=CLI_HTTP_TIMEOUT) as client:
        while True:
            try:
                line = input("> ")
            except (EOFError, KeyboardInterrupt):
                sys.stdout.write("\n")
                return

            stripped = line.strip()
            if not stripped:
                continue
            if stripped == "/exit" or stripped == "exit":
                return
            if stripped == "/new":
                conversation_id = None
                sys.stdout.write("(new conversation)\n")
                continue

            conversation_id = await _send(
                client=client,
                user_id=user_id,
                conversation_id=conversation_id,
                message=stripped,
                document_id=document_id,
            )


async def _send(
    *,
    client: httpx.AsyncClient,
    user_id: str,
    conversation_id: str | None,
    message: str,
    document_id: str | None,
) -> str | None:
    payload: dict[str, object] = {"message": message}
    if conversation_id is not None:
        payload["conversation_id"] = conversation_id
    elif document_id is not None:
        payload["document_id"] = document_id

    next_conversation_id = conversation_id
    try:
        async with client.stream(
            "POST",
            "/api/v1/chat/stream",
            headers={"X-User-Id": user_id, "accept": "text/event-stream"},
            json=payload,
        ) as response:
            if response.status_code != 200:
                body = await response.aread()
                sys.stdout.write(f"[error {response.status_code}] {body.decode()}\n")
                return conversation_id

            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                payload_str = line[len("data: ") :]
                if payload_str == "[DONE]":
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                    break
                frame = cast(dict[str, object], json.loads(payload_str))
                next_conversation_id = _handle_frame(frame, next_conversation_id)
    except httpx.HTTPError as exc:
        sys.stdout.write(f"[transport error] {exc}\n")

    return next_conversation_id


def _handle_frame(frame: dict[str, object], conversation_id: str | None) -> str | None:
    frame_type = frame.get("type")
    if frame_type == "data-conversation":
        data = cast(dict[str, object], frame.get("data", {}))
        return cast(str, data.get("conversationId", conversation_id))
    if frame_type == "text-delta":
        sys.stdout.write(cast(str, frame.get("delta", "")))
        sys.stdout.flush()
        return conversation_id
    if frame_type == "error":
        sys.stdout.write(f"\n[stream error] {frame.get('errorText', '')}\n")
        return conversation_id
    return conversation_id
