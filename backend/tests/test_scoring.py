from __future__ import annotations

from tailorlocal_backend.schemas import Experience, ResumeDocument
from tailorlocal_backend.scoring import calculate_ats_score, source_supported_keywords


JOB = """Machine Learning Engineer
Requirements: Python, SQL, AWS, machine learning, APIs, model deployment
Preferred skills: Python, AWS, model monitoring, data pipelines
"""


def test_score_is_deterministic_and_totals_breakdown() -> None:
    resume = ResumeDocument(
        name="Alex Morgan",
        contact="alex@example.com | +1 555 555 0100 | linkedin.com/in/alex",
        summary="Machine learning engineer building reliable production systems with Python and AWS.",
        skills=["Python", "SQL", "AWS", "Machine Learning", "APIs"],
        experience=[
            Experience(
                company="Example Co",
                role="Machine Learning Engineer",
                bullets=[
                    "Built Python data pipelines that reduced processing time by 35%.",
                    "Deployed machine learning APIs on AWS for production workloads.",
                    "Improved model monitoring coverage across critical services.",
                ],
            )
        ],
    )

    first = calculate_ats_score(resume, JOB)
    second = calculate_ats_score(resume, JOB)

    assert first == second
    assert first.score == sum(item.score for item in first.breakdown)
    assert 0 <= first.score <= 100
    assert {"Python", "AWS", "SQL"}.issubset(set(first.matched_keywords))


def test_source_score_uses_original_document_structure() -> None:
    source = """Alex Morgan
alex@example.com
PROFESSIONAL SUMMARY
Machine learning engineer
SKILLS
Python SQL AWS
EXPERIENCE
- Built data pipelines that improved throughput by 25%
EDUCATION
Example University
"""
    analysis = calculate_ats_score(ResumeDocument(), JOB, source_text=source)

    assert analysis.score == sum(item.score for item in analysis.breakdown)
    assert next(item for item in analysis.breakdown if item.label == "Core sections").score == 15
    assert next(item for item in analysis.breakdown if item.label == "Contact readability").score >= 3


def test_supported_keywords_require_literal_source_evidence() -> None:
    supported = source_supported_keywords(
        ["Python", "model deployment", "Kubernetes", "AWS"],
        "Built Python model deployment pipelines on AWS.",
    )

    assert supported == ["Python", "model deployment", "AWS"]
