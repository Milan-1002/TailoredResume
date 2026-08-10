import numpy as np

from embeddings import embed_text
from llm import call_structured
from models import JDRequirement, MatchResult, ResumeBullet
from prompts import MATCH_JUDGE_SYSTEM_PROMPT

TOP_K = 5


def cosine_similarity(a: list[float], b: list[float]) -> float:
    va, vb = np.array(a), np.array(b)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)


def top_candidates(
    requirement: JDRequirement, bullets: list[ResumeBullet], k: int = TOP_K
) -> list[ResumeBullet]:
    query_text = requirement.text
    if requirement.implied_skills:
        query_text += " " + " ".join(requirement.implied_skills)
    query_vector = embed_text(query_text)

    scored = [
        (cosine_similarity(query_vector, b.embedding), b)
        for b in bullets
        if b.embedding is not None
    ]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [b for _, b in scored[:k]]


def judge_match(requirement: JDRequirement, candidates: list[ResumeBullet]) -> MatchResult:
    if not candidates:
        return MatchResult(
            requirement=requirement.text,
            coverage=0,
            matched_bullet_ids=[],
            reasoning="No resume bullets were found in the master resume to evaluate against this requirement.",
        )

    candidates_text = "\n".join(
        f"- id: {b.id}\n  employer: {b.employer}\n  role: {b.role}\n  text: {b.text}\n  skills: {b.skills}"
        for b in candidates
    )
    user = (
        f"JD requirement: {requirement.text}\n"
        f"Category: {requirement.category}\n"
        f"Importance: {requirement.importance}\n"
        f"Implied skills: {requirement.implied_skills}\n\n"
        f"Candidate resume bullets:\n{candidates_text}"
    )
    result = call_structured(
        system=MATCH_JUDGE_SYSTEM_PROMPT,
        user=user,
        schema=MatchResult,
        tool_name="record_match_result",
    )
    result.requirement = requirement.text
    return result


def match_requirement(requirement: JDRequirement, bullets: list[ResumeBullet]) -> MatchResult:
    candidates = top_candidates(requirement, bullets)
    return judge_match(requirement, candidates)


def match_all(requirements: list[JDRequirement], bullets: list[ResumeBullet]) -> list[MatchResult]:
    return [match_requirement(req, bullets) for req in requirements]
