from __future__ import annotations

import json

import httpx
import pytest

from tailorlocal_backend.main import create_app


VALID_RESUME = {
    "resume": {
        "name": "Alex Morgan",
        "headline": "Python Engineer",
        "contact": "alex@example.com | +1 555 555 0100",
        "summary": "Python engineer delivering reliable production applications.",
        "skills": ["Python", "SQL", "APIs", "AWS", "Testing"],
        "experience": [{
            "company": "Example Co",
            "role": "Software Engineer",
            "location": "",
            "dates": "2022 - Present",
            "bullets": ["Built Python APIs that improved response time by 25%."]
        }],
        "education": [],
        "projects": [],
        "certifications": [],
    }
}


class FakeClient:
    async def list_models(self, provider: str, endpoint: str) -> list[str]:
        return ["llama3.1:latest"]

    async def chat(self, provider: str, endpoint: str, model: str, system: str, prompt: str) -> str:
        return json.dumps(VALID_RESUME)


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(lambda: FakeClient())),  # type: ignore[arg-type]
        base_url="http://testserver",
    )


@pytest.mark.asyncio
async def test_health_models_score_and_generation_contracts() -> None:
    async with _client() as client:
        health = await client.get("/health")
        assert health.status_code == 200
        assert health.json() == {"status": "ok", "service": "tailorlocal-python-backend", "version": "0.1.0"}

        models = await client.post("/api/models", json={"provider": "ollama", "endpoint": "http://127.0.0.1:11434"})
        assert models.status_code == 200
        assert models.json() == {"models": ["llama3.1:latest"], "backend": "python"}

        generated = await client.post("/api/generate", json={
            "provider": "ollama",
            "endpoint": "http://127.0.0.1:11434",
            "model": "llama3.1:latest",
            "resumeText": "Alex Morgan\nPython engineer",
            "jobDescription": "Requirements: Python SQL APIs",
            "targetScore": 0,
            "maxRefinementPasses": 2,
        })
        assert generated.status_code == 200
        body = generated.json()
        assert body["resume"]["name"] == "Alex Morgan"
        assert body["jobDescription"] == "Requirements: Python SQL APIs"
        assert body["refinementPasses"] == 0
        assert body["analysis"]["score"] == sum(item["score"] for item in body["analysis"]["breakdown"])

        scored = await client.post("/api/score", json={"resume": body["resume"], "jobDescription": body["jobDescription"]})
        assert scored.status_code == 200
        assert scored.json()["analysis"] == body["analysis"]


@pytest.mark.asyncio
async def test_api_validation_rejects_blank_text() -> None:
    async with _client() as client:
        response = await client.post("/api/generate", json={
            "provider": "ollama",
            "endpoint": "http://127.0.0.1:11434",
            "model": "llama3.1:latest",
            "resumeText": "   ",
            "jobDescription": "Python",
        })
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_cors_allows_only_local_frontend_origins() -> None:
    async with _client() as client:
        allowed = await client.options(
            "/api/models",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert allowed.status_code == 200
        assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"

        rejected = await client.options(
            "/api/models",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert rejected.status_code == 400
