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
