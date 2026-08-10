from __future__ import annotations

import json

import pytest

from tailorlocal_backend.schemas import GenerationRequest
from tailorlocal_backend.service import ModelResponseError, generate_resume, parse_model_json


def _resume(*, refined: bool) -> str:
    skills = ["Python", "SQL", "AWS", "Machine Learning", "APIs"] if refined else ["Python"]
    bullets = [
        "Built Python data pipelines that improved throughput by 30%.",
        "Deployed machine learning APIs on AWS.",
        "Improved model monitoring for production services.",
    ] if refined else ["Worked on software projects."]
    return json.dumps({
        "resume": {
            "name": "Alex Morgan",
            "headline": "Machine Learning Engineer",
            "contact": "alex@example.com | +1 555 555 0100",
            "summary": "Machine learning engineer building production systems with Python and AWS.",
            "skills": skills,
            "experience": [{"company": "Example Co", "role": "Engineer", "location": "", "dates": "2022 - Present", "bullets": bullets}],
            "education": [{"school": "Example University", "degree": "BS Computer Science", "location": "", "dates": "2022", "details": []}],
            "projects": [],
            "certifications": [],
        }
    })


class FakeClient:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.prompts: list[str] = []

    async def chat(self, provider: str, endpoint: str, model: str, system: str, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.responses.pop(0)


@pytest.mark.asyncio
async def test_generation_uses_snapshot_and_keeps_best_revision() -> None:
    client = FakeClient([_resume(refined=False), _resume(refined=True), _resume(refined=False)])
    request = GenerationRequest(
        provider="ollama",
        endpoint="http://127.0.0.1:11434",
        model="llama3.1:latest",
        resumeText="Alex Morgan\nPython engineer at Example Co\nBS Computer Science",
        jobDescription="Requirements: Python SQL AWS machine learning APIs model monitoring",
        targetScore=100,
        maxRefinementPasses=2,
    )

    result = await generate_resume(request, client)  # type: ignore[arg-type]

    assert result.job_description == request.job_description
    assert result.refinement_passes == 2
    assert "AWS" in result.resume.skills
    assert result.analysis.score >= result.before_analysis.score
    assert len(client.prompts) == 3
    assert all(request.job_description in prompt for prompt in client.prompts)


def test_model_json_parser_accepts_fences_and_rejects_invalid_content() -> None:
    parsed = parse_model_json(f"```json\n{_resume(refined=True)}\n```")
    assert parsed.name == "Alex Morgan"
    assert len(parsed.skills) == 5
    with pytest.raises(ModelResponseError, match="did not return JSON"):
        parse_model_json("not json")
    with pytest.raises(ModelResponseError, match="usable resume"):
        parse_model_json('{"resume": {}}')
