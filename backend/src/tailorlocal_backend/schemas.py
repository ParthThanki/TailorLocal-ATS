"""Validated API contracts shared by the TailorLocal backend."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=_to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        str_strip_whitespace=True,
    )


class Experience(ApiModel):
    company: str = ""
    role: str = ""
    location: str = ""
    dates: str = ""
    bullets: list[str] = Field(default_factory=list)


class Education(ApiModel):
    school: str = ""
    degree: str = ""
    location: str = ""
    dates: str = ""
    details: list[str] = Field(default_factory=list)


class ResumeDocument(ApiModel):
    name: str = ""
    headline: str = ""
    contact: str = ""
    summary: str = ""
    skills: list[str] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    projects: list[Experience] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)


class AtsBreakdownItem(ApiModel):
    label: str
    score: int
    max_score: int
    detail: str


class AtsAnalysis(ApiModel):
    score: int
    matched_keywords: list[str]
    missing_keywords: list[str]
    improvements: list[str]
    breakdown: list[AtsBreakdownItem]


class ProviderConfig(ApiModel):
    provider: Literal["ollama", "openai"]
    endpoint: str = Field(min_length=1, max_length=500)


class ModelListRequest(ProviderConfig):
    pass


class ModelListResponse(ApiModel):
    models: list[str]
    backend: str = "python"


class GenerationRequest(ProviderConfig):
    model: str = Field(min_length=1, max_length=300)
    resume_text: str = Field(min_length=1, max_length=250_000)
    job_description: str = Field(min_length=1, max_length=250_000)
    target_score: int = Field(default=80, ge=0, le=100)
    max_refinement_passes: int = Field(default=2, ge=0, le=4)

    @field_validator("resume_text", "job_description")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must contain readable text")
        return value


class GenerationResponse(ApiModel):
    resume: ResumeDocument
    analysis: AtsAnalysis
    before_analysis: AtsAnalysis
    job_description: str
    refinement_passes: int


class ScoreRequest(ApiModel):
    resume: ResumeDocument
    job_description: str = Field(min_length=1, max_length=250_000)

    @field_validator("job_description")
    @classmethod
    def job_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must contain readable text")
        return value


class ScoreResponse(ApiModel):
    analysis: AtsAnalysis


class HealthResponse(ApiModel):
    status: Literal["ok"] = "ok"
    service: str = "tailorlocal-python-backend"
    version: str
