from pydantic import BaseModel

from embeddings import embed_text
from llm import call_structured, run_concurrent
from match import cosine_similarity
from models import JDRequirement, ParsedJD, ProposedChange, ResumeBullet, ScoreReport
from prompts import GAP_FILL_SYSTEM_PROMPT


class GapFillResult(BaseModel):
    text: str
    rationale: str


def _requirement_lookup(parsed_jd: ParsedJD) -> dict[str, JDRequirement]:
    return {req.text: req for req in parsed_jd.requirements}


def _best_candidate(requirement: JDRequirement, bullets: list[ResumeBullet]) -> ResumeBullet | None:
    query_text = requirement.text
    if requirement.implied_skills:
        query_text += " " + " ".join(requirement.implied_skills)
    query_vector = embed_text(query_text)

    scored = [
        (cosine_similarity(query_vector, b.embedding), b)
        for b in bullets
        if b.embedding is not None
    ]
    if not scored:
        return None
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return scored[0][1]


def generate_keyword_injections(
    parsed_jd: ParsedJD,
    report: ScoreReport,
    bullets: list[ResumeBullet],
    excluded_bullet_ids: set[str],
) -> list[ProposedChange]:
    """For every JD requirement with coverage==0 (a total evidence gap), picks the best-matching
    bullet not already used elsewhere and has the LLM liberally rewrite it to plausibly cover the
    missing keyword/skill. must_have gaps are processed before nice_to_have gaps. Each bullet can
    only be claimed by one gap within this step (in addition to bullets already excluded from
    earlier orchestration steps)."""
    requirement_by_text = _requirement_lookup(parsed_jd)

    gaps = [
        requirement_by_text[result.requirement]
        for result in report.per_requirement
        if result.coverage == 0 and result.requirement in requirement_by_text
    ]
    gaps.sort(key=lambda req: 0 if req.importance == "must_have" else 1)

    # Bullet selection must stay sequential — each gap's candidate pool depends on
    # which bullets earlier gaps already claimed — but this step is cheap (local
    # embedding similarity, no LLM call), so the sequencing costs nothing.
    claimed_bullet_ids: set[str] = set(excluded_bullet_ids)
    assignments: list[tuple[JDRequirement, ResumeBullet]] = []
    for requirement in gaps:
        available = [b for b in bullets if b.id not in claimed_bullet_ids]
        best = _best_candidate(requirement, available)
        if best is None:
            continue

        # Claim immediately on selection so a later gap in this same step can't also
        # pick this bullet, even if this gap's rewrite ends up being a no-op below.
        claimed_bullet_ids.add(best.id)
        assignments.append((requirement, best))

    def _generate(assignment: tuple[JDRequirement, ResumeBullet]) -> GapFillResult:
        requirement, best = assignment
        user = (
            f"JD requirement (currently unmet): {requirement.text}\n"
            f"Category: {requirement.category}\n"
            f"Importance: {requirement.importance}\n"
            f"Implied skills: {requirement.implied_skills}\n\n"
            f"Closest existing bullet to extend:\n"
            f"- employer: {best.employer}\n"
            f"  role: {best.role}\n"
            f"  text: {best.text}\n"
            f"  skills: {best.skills}"
        )
        return call_structured(
            system=GAP_FILL_SYSTEM_PROMPT,
            user=user,
            schema=GapFillResult,
            tool_name="record_gap_fill",
        )

    # The assignment (who gets rewritten) is already fixed above, so the slow LLM
    # calls themselves have no interdependency and can run concurrently.
    results = run_concurrent(_generate, assignments)

    changes: list[ProposedChange] = []
    for (requirement, best), result in zip(assignments, results):
        if result.text.strip() == best.text.strip():
            continue

        changes.append(
            ProposedChange(
                id=f"{best.id}__keyword_injection",
                bullet_id=best.id,
                employer=best.employer,
                role=best.role,
                change_type="keyword_injection",
                original_text=best.text,
                proposed_text=result.text,
                rationale=result.rationale,
                related_requirement=requirement.text,
                requires_confirmation=False,
                confirmation_prompt=None,
            )
        )

    return changes
