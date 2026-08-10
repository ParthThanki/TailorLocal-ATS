"""Deterministic, job-specific ATS compatibility scoring."""

from __future__ import annotations

import math
import re
from collections import Counter

from .schemas import AtsAnalysis, AtsBreakdownItem, ResumeDocument

STOP_WORDS = set(
    """
    a an and are as at be been being but by can could did do does doing for from had has have having
    he her hers him his how i if in into is it its itself may might more most must my no nor not of on
    or our ours ourselves out over own same she should so some such than that the their theirs them
    themselves then there these they this those through to too under until up very was we were what
    when where which while who whom why will with would you your yours yourself yourselves
    ability about across all also any apply based both candidate candidates company day each either
    environment etc excellent include includes including job jobs knowledge looking position preferred
    qualification qualifications required requirement requirements responsibility responsibilities
    role roles skill skills strong team teams using want well work working years
    """.split()
)
SHORT_SKILL_TERMS = {"ai", "bi", "c", "go", "hr", "it", "ml", "qa", "r", "ui", "ux"}
DISPLAY_KEYWORDS = {
    "ai": "AI", "api": "API", "apis": "APIs", "aws": "AWS", "bi": "BI",
    "cplusplus": "C++", "csharp": "C#", "crm": "CRM", "css": "CSS",
    "dotnet": ".NET", "erp": "ERP", "gcp": "GCP", "html": "HTML", "hr": "HR",
    "javascript": "JavaScript", "ml": "ML", "nextjs": "Next.js", "nodejs": "Node.js",
    "powerbi": "Power BI", "qa": "QA", "saas": "SaaS", "sql": "SQL",
    "python": "Python", "typescript": "TypeScript", "ui": "UI", "ux": "UX",
}


def canonical_text(value: str) -> str:
    value = value.lower()
    replacements = (
        (r"c\+\+", " cplusplus "),
        (r"c#", " csharp "),
        (r"\.net\b", " dotnet "),
        (r"node\.?js\b", " nodejs "),
        (r"next\.?js\b", " nextjs "),
        (r"power\s*bi\b", " powerbi "),
    )
    for pattern, replacement in replacements:
        value = re.sub(pattern, replacement, value)
    return re.sub(r"[^a-z0-9+#.-]+", " ", value).strip()


def stem_token(value: str) -> str:
    if len(value) > 6 and value.endswith("ies"):
        return f"{value[:-3]}y"
    if len(value) > 7 and value.endswith("ing"):
        return re.sub(r"(.)\1$", r"\1", value[:-3])
    if len(value) > 6 and value.endswith("ed"):
        return re.sub(r"(.)\1$", r"\1", value[:-2])
    if len(value) > 5 and value.endswith("s") and not re.search(r"(ss|us|is)$", value):
        return value[:-1]
    return value


ACTION_VERBS = {
    stem_token(value)
    for value in """
    achieved accelerated automated built created delivered designed developed drove enabled established
    expanded generated grew implemented improved increased launched led managed migrated optimized
    orchestrated reduced redesigned resolved saved scaled shipped simplified spearheaded streamlined
    transformed upgraded
    """.split()
}


def tokens_for(value: str) -> list[str]:
    return [
        token.strip(".-")
        for token in re.findall(r"[a-z][a-z0-9+.#-]*", canonical_text(value))
        if token.strip(".-")
    ]


def is_significant_token(value: str) -> bool:
    return value not in STOP_WORDS and (len(value) >= 3 or value in SHORT_SKILL_TERMS)


def keyword_label(value: str) -> str:
    return " ".join(DISPLAY_KEYWORDS.get(word, word) for word in value.split(" "))


def resume_as_text(resume: ResumeDocument) -> str:
    values = [resume.name, resume.headline, resume.contact, resume.summary, " ".join(resume.skills)]
    for item in resume.experience:
        values.extend([item.company, item.role, item.location, *item.bullets])
    for item in resume.projects:
        values.extend([item.company, item.role, *item.bullets])
    for item in resume.education:
        values.extend([item.school, item.degree, item.location, *item.details])
    values.extend(resume.certifications)
    return " \n".join(values)


def _js_round(value: float) -> int:
    return math.floor(value + 0.5)


def calculate_ats_score(
    resume: ResumeDocument,
    job_description: str,
    *,
    source_text: str | None = None,
) -> AtsAnalysis:
    source_text = source_text.strip() if source_text and source_text.strip() else None
    scored_resume_text = source_text or resume_as_text(resume)
    job_tokens = tokens_for(job_description)
    priority_tokens: set[str] = set()
    for line in job_description.splitlines():
        if re.search(r"skills?|requirements?|qualifications?|must have|preferred|what you bring", line, re.I):
            priority_tokens.update(
                stem_token(token)
                for token in tokens_for(line)
                if is_significant_token(token)
            )

    significant = [token for token in job_tokens if is_significant_token(token)]
    counts = Counter(stem_token(token) for token in significant)
    labels: dict[str, str] = {}
    for token in significant:
        labels.setdefault(stem_token(token), keyword_label(token))
    unigram_terms = sorted(
        (
            {
                "key": key,
                "label": labels.get(key, key),
                "weight": 1 + math.log2(count) + (0.8 if key in priority_tokens else 0),
            }
            for key, count in counts.items()
        ),
        key=lambda item: (-float(item["weight"]), str(item["label"])),
    )[:28]

    phrase_counts: dict[str, dict[str, int | str]] = {}
    for first, second in zip(job_tokens, job_tokens[1:]):
        if not is_significant_token(first) or not is_significant_token(second):
            continue
        key = f"{stem_token(first)} {stem_token(second)}"
        current = phrase_counts.setdefault(
            key,
            {"count": 0, "label": f"{keyword_label(first)} {keyword_label(second)}"},
        )
        current["count"] = int(current["count"]) + 1
    phrase_terms = sorted(
        (
            {
                "key": key,
                "label": value["label"],
                "weight": 1.4 + math.log2(int(value["count"])),
            }
            for key, value in phrase_counts.items()
            if int(value["count"]) > 1
        ),
        key=lambda item: -float(item["weight"]),
    )[:4]

    terms = [*unigram_terms, *phrase_terms]
    resume_sequence = [stem_token(token) for token in tokens_for(scored_resume_text)]
    resume_token_set = set(resume_sequence)
    resume_token_text = f" {' '.join(resume_sequence)} "

    def matched(term: dict[str, object]) -> bool:
        key = str(term["key"])
        return f" {key} " in resume_token_text if " " in key else key in resume_token_set

    matched_terms = [term for term in terms if matched(term)]
    missing_terms = [term for term in terms if not matched(term)]
    total_weight = sum(float(term["weight"]) for term in terms)
    matched_weight = sum(float(term["weight"]) for term in matched_terms)
    keyword_score = _js_round(55 * matched_weight / total_weight) if total_weight else 0

    section_score = 0
    if source_text:
        patterns = (
            (r"\b(professional summary|career summary|summary|profile|objective)\b", 3),
            (r"\b(technical skills|core skills|key skills|skills|competencies|technologies)\b", 4),
            (r"\b(professional experience|work experience|employment history|work history|experience)\b", 5),
            (r"\b(education|academic background|qualifications)\b", 3),
        )
        section_score = sum(points for pattern, points in patterns if re.search(pattern, source_text, re.I))
    else:
        section_score += 3 if len(resume.summary) >= 80 else 2 if len(resume.summary) >= 35 else 0
        section_score += 4 if len(resume.skills) >= 5 else 2 if len(resume.skills) >= 3 else 0
        section_score += 5 if resume.experience else 3 if resume.projects else 0
        section_score += 3 if resume.education else 0

    bullets = [
        bullet
        for item in [*resume.experience, *resume.projects]
        for bullet in item.bullets
        if bullet
    ]
    impact_score = 0
    if source_text:
        source_tokens = [stem_token(token) for token in tokens_for(source_text)]
        action_hits = sum(token in ACTION_VERBS for token in source_tokens)
        metric_hits = len(re.findall(r"(?:[$£€]|\b\d+(?:[.,]\d+)?%\b)", source_text))
        visible_bullets = len(re.findall(r"[•▪◦]", source_text))
        if not visible_bullets:
            visible_bullets = sum(bool(re.match(r"^\s*[-*]", line)) for line in source_text.splitlines())
        impact_score = min(7, action_hits) + min(5, metric_hits * 2) + (3 if visible_bullets >= 3 else 2 if visible_bullets else 0)
    elif bullets:
        action_ratio = sum(
            bool(tokens_for(bullet)) and stem_token(tokens_for(bullet)[0]) in ACTION_VERBS
            for bullet in bullets
        ) / len(bullets)
        metric_ratio = sum(bool(re.search(r"(?:[$£€]|\b\d+(?:[.,]\d+)?%?\b)", bullet)) for bullet in bullets) / len(bullets)
        concise_ratio = sum(8 <= len(bullet.strip().split()) <= 32 for bullet in bullets) / len(bullets)
        impact_score = (
            _js_round(7 * min(action_ratio / 0.6, 1))
            + _js_round(5 * min(metric_ratio / 0.35, 1))
            + _js_round(3 * min(concise_ratio / 0.8, 1))
        )

    format_score = 10
    if source_text:
        headings = sum(
            bool(re.search(pattern, source_text, re.I))
            for pattern in (
                r"\b(summary|profile|objective)\b",
                r"\b(skills|competencies|technologies)\b",
                r"\b(experience|employment history|work history)\b",
                r"\b(education|academic background)\b",
            )
        )
        line_count = sum(bool(line.strip()) for line in source_text.splitlines())
        format_score = (
            (4 if len(source_text) >= 250 else 2 if len(source_text) >= 100 else 0)
            + min(4, headings)
            + (2 if line_count >= 6 or re.search(r"[•▪◦]", source_text) else 1 if line_count >= 3 else 0)
        )

    contact_score = 0
    contact_text = source_text or resume.contact
    contact_score += 2 if re.search(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", contact_text, re.I) else 0
    contact_score += 1 if re.search(r"\+?\d[\d\s().-]{7,}\d", contact_text) else 0
    contact_score += 1 if re.search(r"linkedin|https?://|www\.", contact_text, re.I) else 0
    has_name = bool(
        re.search(r"^[\s\S]{0,250}\b[a-z]{2,}(?:\s+[a-z]{2,}){1,3}\b", source_text, re.I)
        if source_text
        else resume.name.strip()
    )
    contact_score += 1 if has_name else 0

    breakdown = [
        AtsBreakdownItem(label="Keyword alignment", score=keyword_score, max_score=55, detail=f"{len(matched_terms)} of {len(terms)} prioritized terms found"),
        AtsBreakdownItem(label="Core sections", score=section_score, max_score=15, detail="Summary, skills, experience, and education completeness"),
        AtsBreakdownItem(label="Impact evidence", score=impact_score, max_score=15, detail="Action-led, concise bullets with measurable outcomes"),
        AtsBreakdownItem(label="ATS-safe format", score=format_score, max_score=10, detail="Extractable text, recognizable headings, and parseable structure" if source_text else "Single column, standard headings, and selectable text"),
        AtsBreakdownItem(label="Contact readability", score=contact_score, max_score=5, detail="Name, email, phone, and professional link detection"),
    ]
    improvements: list[str] = []
    if keyword_score < 40:
        improvements.append("Review the missing role terms and add only those the source experience supports.")
    if section_score < 12:
        improvements.append("Complete the core resume sections supported by the source document.")
    if impact_score < 10:
        improvements.append("Use more action-led bullets and preserve measurable results from the original resume.")
    if contact_score < 4:
        improvements.append("Check that email, phone number, and professional profile details are easy to parse.")
    return AtsAnalysis(
        score=sum(item.score for item in breakdown),
        matched_keywords=[str(term["label"]) for term in matched_terms],
        missing_keywords=[str(term["label"]) for term in missing_terms],
        improvements=improvements,
        breakdown=breakdown,
    )


def source_supported_keywords(keywords: list[str], source_text: str) -> list[str]:
    source_tokens = {stem_token(token) for token in tokens_for(source_text)}
    supported: list[str] = []
    for keyword in keywords:
        keyword_tokens = [
            stem_token(token)
            for token in tokens_for(keyword)
            if is_significant_token(token)
        ]
        if keyword_tokens and all(token in source_tokens for token in keyword_tokens):
            supported.append(keyword)
    return supported
