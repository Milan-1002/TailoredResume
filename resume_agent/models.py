from typing import Literal

from pydantic import BaseModel


class ResumeBullet(BaseModel):
    id: str
    employer: str
    role: str
    start_date: str
    end_date: str | None
    text: str
    skills: list[str]
    seniority_signal: str | None
    quantified_outcome: str | None
    embedding: list[float] | None = None
    source_paragraph_index: int | None = None


class JDRequirement(BaseModel):
    text: str
    category: Literal["hard_skill", "soft_skill", "experience_years", "domain_knowledge"]
    importance: Literal["must_have", "nice_to_have"]
    implied_skills: list[str]


class ParsedJD(BaseModel):
    role_title: str
    seniority_level: str
    requirements: list[JDRequirement]


class MatchResult(BaseModel):
    requirement: str
    coverage: Literal[0, 1, 2]
    matched_bullet_ids: list[str]
    reasoning: str


class ScoreReport(BaseModel):
    keyword_coverage_pct: float
    substantive_fit_score: float
    must_have_gaps: list[str]
    per_requirement: list[MatchResult]


class BulletForRewrite(BaseModel):
    bullet: ResumeBullet
    satisfied_requirements: list[str]
    emphasis: Literal["high", "light"]


class RewrittenBullet(BaseModel):
    bullet_id: str
    employer: str
    role: str
    text: str


class TailoredResume(BaseModel):
    bullets: list[RewrittenBullet]


class ProposedChange(BaseModel):
    id: str  # f"{bullet_id}__{change_type}"
    bullet_id: str
    employer: str
    role: str
    change_type: Literal["rewrite", "keyword_injection", "tech_swap"]
    original_text: str
    proposed_text: str
    rationale: str
    related_requirement: str | None
    requires_confirmation: bool = False
    confirmation_prompt: str | None = None


class TailorAnalyzeResponse(BaseModel):
    parsed_jd: ParsedJD
    report: ScoreReport
    proposed_changes: list[ProposedChange]


class FinalizeBullet(BaseModel):
    bullet_id: str
    text: str


class FinalizeRequest(BaseModel):
    bullets: list[FinalizeBullet]


class FinalizeResponse(BaseModel):
    docx_url: str | None
    pdf_url: str | None
    edited_count: int
    skipped_count: int
