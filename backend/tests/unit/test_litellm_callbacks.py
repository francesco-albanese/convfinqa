from typing import Any
from unittest.mock import MagicMock, patch

import litellm
import pytest


@pytest.mark.unit
def test_register_callbacks_adds_langfuse_otel() -> None:
    original = litellm.callbacks
    litellm.callbacks = []
    try:
        from convfinqa.adapters.llm.litellm_adapter import _register_callbacks

        _register_callbacks()
        assert "langfuse_otel" in litellm.callbacks
    finally:
        litellm.callbacks = original


@pytest.mark.unit
def test_register_callbacks_is_idempotent() -> None:
    from convfinqa.adapters.llm.litellm_adapter import (
        _attach_cost_to_current_generation,
        _log_llm_failure,
        _register_callbacks,
    )

    original_callbacks = litellm.callbacks
    original_successes = litellm.success_callback
    original_failures = litellm.failure_callback
    litellm.callbacks = ["langfuse_otel"]
    litellm.success_callback = [_attach_cost_to_current_generation]
    litellm.failure_callback = [_log_llm_failure]
    try:
        _register_callbacks()
        assert litellm.callbacks.count("langfuse_otel") == 1
        assert litellm.success_callback.count(_attach_cost_to_current_generation) == 1
        assert litellm.failure_callback.count(_log_llm_failure) == 1
    finally:
        litellm.callbacks = original_callbacks
        litellm.success_callback = original_successes
        litellm.failure_callback = original_failures


@pytest.mark.unit
async def test_log_llm_failure_logs_structured_warning() -> None:
    from convfinqa.adapters.llm.litellm_adapter import _log_llm_failure

    with patch("convfinqa.adapters.llm.litellm_adapter.LITELLM_LOG") as mock_log:
        await _log_llm_failure(
            kwargs={"model": "bedrock/claude-haiku"},
            exception=ValueError("connection timeout"),
            start_time=None,
            end_time=None,
        )

    mock_log.warning.assert_called_once()
    call_args = mock_log.warning.call_args
    assert call_args.args[0] == "llm_failure"
    extra: dict[str, Any] = call_args.kwargs.get("extra", {})
    assert extra["exc_type"] == "ValueError"
    assert extra["exc_message"] == "connection timeout"
    assert extra["model"] == "bedrock/claude-haiku"


@pytest.mark.unit
async def test_log_llm_failure_falls_back_to_unknown_model() -> None:
    from convfinqa.adapters.llm.litellm_adapter import _log_llm_failure

    with patch("convfinqa.adapters.llm.litellm_adapter.LITELLM_LOG") as mock_log:
        await _log_llm_failure(
            kwargs={},
            exception=RuntimeError("oops"),
            start_time=None,
            end_time=None,
        )

    extra: dict[str, Any] = mock_log.warning.call_args.kwargs.get("extra", {})
    assert extra["model"] == "unknown"


@pytest.mark.unit
def test_attach_cost_updates_current_generation() -> None:
    from convfinqa.adapters.llm.litellm_adapter import (
        _attach_cost_to_current_generation,
    )

    response = MagicMock()
    response.usage = {"prompt_tokens": 100, "completion_tokens": 50}
    langfuse_client = MagicMock()

    with (
        patch(
            "convfinqa.adapters.llm.litellm_adapter.litellm.completion_cost",
            return_value=0.00042,
        ) as completion_cost,
        patch("langfuse.get_client", return_value=langfuse_client),
    ):
        _attach_cost_to_current_generation(
            kwargs={"model": "bedrock/claude-haiku"},
            response=response,
            start_time=None,
            end_time=None,
        )

    completion_cost.assert_called_once_with(
        model="bedrock/claude-haiku",
        completion_response=response,
    )
    langfuse_client.update_current_generation.assert_called_once_with(
        cost_details={"input": 0.0, "output": 0.0, "total": 0.00042}
    )


@pytest.mark.unit
def test_attach_cost_noops_without_usage() -> None:
    from convfinqa.adapters.llm.litellm_adapter import (
        _attach_cost_to_current_generation,
    )

    response = MagicMock()
    response.usage = None

    with (
        patch(
            "convfinqa.adapters.llm.litellm_adapter.litellm.completion_cost"
        ) as completion_cost,
        patch("langfuse.get_client") as get_client,
    ):
        _attach_cost_to_current_generation(
            kwargs={"model": "gemini/gemini-2.5-flash"},
            response=response,
            start_time=None,
            end_time=None,
        )

    completion_cost.assert_not_called()
    get_client.assert_not_called()


@pytest.mark.unit
async def test_open_stream_passes_generation_name_in_metadata() -> None:
    from unittest.mock import AsyncMock

    from convfinqa.adapters.llm.litellm_adapter import _open_stream

    captured_kwargs: dict[str, Any] = {}

    async def fake_acompletion(**kwargs: Any) -> AsyncMock:
        captured_kwargs.update(kwargs)
        mock = AsyncMock()
        mock.__aiter__ = MagicMock(return_value=iter([]))
        return mock

    with patch("convfinqa.adapters.llm.litellm_adapter.litellm") as mock_litellm:
        mock_litellm.acompletion = fake_acompletion
        await _open_stream(
            model="bedrock/claude-haiku",
            wire_messages=[{"role": "user", "content": "hi"}],
            timeout_seconds=30.0,
            max_output_tokens=1000,
            generation_name="iteration-0",
            trace_user_id="user-1",
            session_id="conversation-1",
            environment="test",
        )

    assert captured_kwargs.get("metadata") == {
        "generation_name": "iteration-0",
        "trace_user_id": "user-1",
        "session_id": "conversation-1",
        "tags": ["environment:test"],
    }


@pytest.mark.unit
async def test_open_stream_omits_metadata_when_no_generation_name() -> None:
    from unittest.mock import AsyncMock

    from convfinqa.adapters.llm.litellm_adapter import _open_stream

    captured_kwargs: dict[str, Any] = {}

    async def fake_acompletion(**kwargs: Any) -> AsyncMock:
        captured_kwargs.update(kwargs)
        mock = AsyncMock()
        mock.__aiter__ = MagicMock(return_value=iter([]))
        return mock

    with patch("convfinqa.adapters.llm.litellm_adapter.litellm") as mock_litellm:
        mock_litellm.acompletion = fake_acompletion
        await _open_stream(
            model="bedrock/claude-haiku",
            wire_messages=[{"role": "user", "content": "hi"}],
            timeout_seconds=30.0,
            max_output_tokens=1000,
        )

    assert "metadata" not in captured_kwargs
