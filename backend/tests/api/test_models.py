import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


async def _client(app: FastAPI) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_list_models_returns_allowlist_and_default(app: FastAPI) -> None:
    async with await _client(app) as client:
        response = await client.get("/api/v1/models")

    assert response.status_code == 200
    body = response.json()
    assert body["default"] in body["models"]
    assert body["models"] == [
        "bedrock/eu.anthropic.claude-haiku-4-5-20251001-v1:0",
        "gemini/gemini-2.5-flash",
    ]
    assert body["default"] == "bedrock/eu.anthropic.claude-haiku-4-5-20251001-v1:0"
