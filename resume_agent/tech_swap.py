from pydantic import BaseModel

from embeddings import embed_text
from llm import call_structured, run_concurrent
from match import cosine_similarity
from models import JDRequirement, ParsedJD, ProposedChange, ResumeBullet, ScoreReport
from prompts import TECH_SWAP_SYSTEM_PROMPT

RECENT_ROLE_COUNT = 2


class TechSwapResult(BaseModel):
    feasible: bool
    sibling_skill: str | None
    proposed_text: str | None
    rationale: str | None


def _requirement_lookup(parsed_jd: ParsedJD) -> dict[str, JDRequirement]:
    return {req.text: req for req in parsed_jd.requirements}


def _recent_roles(bullets: list[ResumeBullet]) -> list[tuple[str, str]]:
    """Same pattern as rewrite.py's RECENT_ROLE_COUNT logic: the first RECENT_ROLE_COUNT
    distinct (employer, role) pairs encountered, in resume order (most-recent-first)."""
    recent_roles: list[tuple[str, str]] = []
    for b in bullets:
        key = (b.employer, b.role)
        if key not in recent_roles:
            recent_roles.append(key)
        if len(recent_roles) >= RECENT_ROLE_COUNT:
            break
    return recent_roles


def _best_recent_candidate(
    requirement: JDRequirement, recent_bullets: list[ResumeBullet]
) -> ResumeBullet | None:
    query_text = requirement.text
    if requirement.implied_skills:
        query_text += " " + " ".join(requirement.implied_skills)
    query_vector = embed_text(query_text)

    scored = [
        (cosine_similarity(query_vector, b.embedding), b)
        for b in recent_bullets
        if b.embedding is not None
    ]
    if not scored:
        return None
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return scored[0][1]


def generate_tech_swaps(
    parsed_jd: ParsedJD, report: ScoreReport, bullets: list[ResumeBullet]
) -> list[ProposedChange]:
    """For hard_skill requirements with coverage 0 or 1, restricted to bullets in the candidate's
    RECENT_ROLE_COUNT most recent (employer, role) pairs, proposes reframing the best-matching
    recent bullet around the JD's wanted technology if the LLM judges a genuinely plausible
    sibling/adjacent technology exists elsewhere in the candidate's full bullet history. Each
    proposed swap requires frontend confirmation before it can be accepted."""
    requirement_by_text = _requirement_lookup(parsed_jd)

    weak_hard_skill_reqs = [
        requirement_by_text[result.requirement]
        for result in report.per_requirement
        if result.coverage in (0, 1)
        and result.requirement in requirement_by_text
        and requirement_by_text[result.requirement].category == "hard_skill"
    ]
    if not weak_hard_skill_reqs:
        return []

    recent_roles = _recent_roles(bullets)
    recent_bullets = [b for b in bullets if (b.employer, b.role) in recent_roles]
    older_bullets = [b for b in bullets if (b.employer, b.role) not in recent_roles]
    if not recent_bullets or not older_bullets:
        return []

    other_bullets_text = "\n".join(
        f"- employer: {b.employer}\n  role: {b.role}\n  text: {b.text}\n  skills: {b.skills}"
        for b in older_bullets
    )

    # Selection must stay sequential — each requirement's candidate pool depends on
    # which recent bullets earlier requirements already claimed — but it's cheap
    # (local embedding similarity, no LLM call). Bullets are claimed on selection
    # (not on success) so the slow LLM calls below have no interdependency and can
    # run concurrently; the trade-off is that a bullet judged infeasible for one
    # requirement is no longer retried against a different one.
    used_bullet_ids: set[str] = set()
    assignments: list[tuple[JDRequirement, ResumeBullet]] = []
    for requirement in weak_hard_skill_reqs:
        candidates = [b for b in recent_bullets if b.id not in used_bullet_ids]
        target = _best_recent_candidate(requirement, candidates)
        if target is None:
            continue
        used_bullet_ids.add(target.id)
        assignments.append((requirement, target))

    def _generate(assignment: tuple[JDRequirement, ResumeBullet]) -> TechSwapResult:
        requirement, target = assignment
        user = (
            f"JD requirement (weak/missing in candidate's recent roles): {requirement.text}\n"
            f"Implied skills: {requirement.implied_skills}\n\n"
            f"Target bullet to potentially reframe (from a recent role):\n"
            f"- employer: {target.employer}\n"
            f"  role: {target.role}\n"
            f"  text: {target.text}\n"
            f"  skills: {target.skills}\n\n"
            f"Candidate's other bullets (earlier roles — evidence pool for sibling skills):\n"
            f"{other_bullets_text}"
        )
        return call_structured(
            system=TECH_SWAP_SYSTEM_PROMPT,
            user=user,
            schema=TechSwapResult,
            tool_name="record_tech_swap",
        )

    results = run_concurrent(_generate, assignments)

    changes: list[ProposedChange] = []
    for (requirement, target), result in zip(assignments, results):
        if not result.feasible or not result.proposed_text:
            continue
        if result.proposed_text.strip() == target.text.strip():
            continue

        sibling_note = f" using their {result.sibling_skill} experience" if result.sibling_skill else ""
        changes.append(
            ProposedChange(
                id=f"{target.id}__tech_swap",
                bullet_id=target.id,
                employer=target.employer,
                role=target.role,
                change_type="tech_swap",
                original_text=target.text,
                proposed_text=result.proposed_text,
                rationale=result.rationale or f"Reframed around {requirement.text}{sibling_note}.",
                related_requirement=requirement.text,
                requires_confirmation=True,
                confirmation_prompt=(
                    f"This rewrites a bullet to claim \"{requirement.text}\" experience"
                    f"{sibling_note}. Do you actually know this well enough to defend it "
                    "in an interview?"
                ),
            )
        )

    return changes
