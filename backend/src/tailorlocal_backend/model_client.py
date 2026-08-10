"""HTTP client for local Ollama and OpenAI-compatible model servers."""

from __future__ import annotations

import ipaddress
from urllib.parse import urlsplit

import httpx


class LocalModelError(RuntimeError):
    """Raised when a local model server cannot complete a request."""


def validated_local_endpoint(endpoint: str) -> str:
    value = endpoint.strip().rstrip("/")
    parsed = urlsplit(value)
    if parsed.scheme != "http" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("The model endpoint must be an HTTP loopback address.")
    hostname = parsed.hostname.lower()
    try:
        is_loopback = ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        is_loopback = hostname == "localhost"
    if not is_loopback:
        raise ValueError("Only localhost and loopback model endpoints are allowed.")
    return value


class LocalModelClient:
    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._transport = transport

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            transport=self._transport,
            timeout=httpx.Timeout(300.0, connect=8.0),
            trust_env=False,
        )

    async def list_models(self, provider: str, endpoint: str) -> list[str]:
        base = validated_local_endpoint(endpoint)
        path = "/api/tags" if provider == "ollama" else "/v1/models"
        try:
            async with self._client() as client:
                response = await client.get(f"{base}{path}")
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise LocalModelError(f"Could not connect to the local model server: {exc}") from exc
        if provider == "ollama":
            models = [str(item.get("name", "")).strip() for item in payload.get("models", [])]
        else:
            models = [str(item.get("id", "")).strip() for item in payload.get("data", [])]
        return list(dict.fromkeys(model for model in models if model))

    async def chat(self, provider: str, endpoint: str, model: str, system: str, prompt: str) -> str:
        base = validated_local_endpoint(endpoint)
        messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
        try:
            async with self._client() as client:
                if provider == "ollama":
                    response = await client.post(
                        f"{base}/api/chat",
                        json={
                            "model": model,
                            "stream": False,
                            "format": "json",
                            "options": {"temperature": 0.1, "num_ctx": 16384, "num_predict": 4096},
                            "messages": messages,
                        },
                    )
                    response.raise_for_status()
                    payload = response.json()
                    content = payload.get("message", {}).get("content") or payload.get("response")
                else:
                    request = {"model": model, "temperature": 0.1, "messages": messages}
                    response = await client.post(
                        f"{base}/v1/chat/completions",
                        json={**request, "response_format": {"type": "json_object"}},
                    )
                    if response.status_code in {400, 422}:
                        response = await client.post(f"{base}/v1/chat/completions", json=request)
                    response.raise_for_status()
                    payload = response.json()
                    choices = payload.get("choices") or []
                    content = choices[0].get("message", {}).get("content") if choices else None
        except (httpx.HTTPError, ValueError) as exc:
            raise LocalModelError(f"The local model request failed: {exc}") from exc
        if not isinstance(content, str) or not content.strip():
            raise LocalModelError("The local model returned an empty response.")
        return content
