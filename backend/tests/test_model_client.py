from __future__ import annotations

import json

import httpx
import pytest

from tailorlocal_backend.model_client import LocalModelClient, validated_local_endpoint


def test_endpoint_restriction_allows_only_http_loopback() -> None:
    assert validated_local_endpoint("http://127.0.0.1:11434/") == "http://127.0.0.1:11434"
    assert validated_local_endpoint("http://localhost:1234") == "http://localhost:1234"
    with pytest.raises(ValueError, match="loopback"):
        validated_local_endpoint("https://127.0.0.1:11434")
    with pytest.raises(ValueError, match="loopback"):
        validated_local_endpoint("http://example.com:11434")


@pytest.mark.asyncio
async def test_ollama_models_and_chat_are_normalized() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "llama3.1:latest"}, {"name": "llama3.1:latest"}]})
        assert request.url.path == "/api/chat"
        payload = json.loads(request.content)
        assert payload["stream"] is False
        assert payload["format"] == "json"
        return httpx.Response(200, json={"message": {"content": '{"resume": {}}'}})

    client = LocalModelClient(httpx.MockTransport(handler))

    assert await client.list_models("ollama", "http://127.0.0.1:11434") == ["llama3.1:latest"]
    assert await client.chat("ollama", "http://127.0.0.1:11434", "llama3.1:latest", "system", "prompt") == '{"resume": {}}'


@pytest.mark.asyncio
async def test_openai_compatible_chat_retries_without_response_format() -> None:
    attempts = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"data": [{"id": "local-model"}]})
        attempts += 1
        payload = json.loads(request.content)
        if "response_format" in payload:
            return httpx.Response(400, json={"error": "unsupported"})
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    client = LocalModelClient(httpx.MockTransport(handler))

    assert await client.list_models("openai", "http://localhost:1234") == ["local-model"]
    assert await client.chat("openai", "http://localhost:1234", "local-model", "system", "prompt") == "ok"
    assert attempts == 2
