from llm import call_structured
from models import BulletForRewrite, MatchResult, ResumeBullet, RewrittenBullet, TailoredResume
from prompts import REWRITE_SYSTEM_PROMPT

RECENT_ROLE_COUNT = 2


def select_bullets_for_rewrite(
    bullets: list[ResumeBullet], match_results: list[MatchResult]
) -> list[BulletForRewrite]:
    """Builds the only input rewrite_bullets() is allowed to see: bullets that matched
    a requirement with coverage >= 1. Bullets tied to coverage-0 requirements, and the
    raw JD/requirement list itself, never reach this list.

    Preserves the original resume order (same order as `bullets`) rather than the
    match-results order, so the rewrite step never reshuffles sections. The first
    RECENT_ROLE_COUNT distinct (employer, role) pairs encountered — i.e. the most
    recent roles, since resumes list roles most-recent-first — get "high" emphasis;
    older roles get "light" emphasis.
    """
    satisfied_requirements_by_bullet: dict[str, list[str]] = {}
    for result in match_results:
        if result.coverage < 1:
            continue
        for bullet_id in result.matched_bullet_ids:
            satisfied_requirements_by_bullet.setdefault(bullet_id, []).append(result.requirement)

    recent_roles: list[tuple[str, str]] = []
    for b in bullets:
        key = (b.employer, b.role)
        if key not in recent_roles:
            recent_roles.append(key)
        if len(recent_roles) >= RECENT_ROLE_COUNT:
            break

    return [
        BulletForRewrite(
            bullet=bullet,
            satisfied_requirements=satisfied_requirements_by_bullet[bullet.id],
            emphasis="high" if (bullet.employer, bullet.role) in recent_roles else "light",
        )
        for bullet in bullets
        if bullet.id in satisfied_requirements_by_bullet
    ]


def rewrite_bullets(matched_bullets: list[BulletForRewrite]) -> TailoredResume:
    if not matched_bullets:
        return TailoredResume(bullets=[])

    groups_text = "\n\n".join(
        f"- id: {mb.bullet.id}\n"
        f"  employer: {mb.bullet.employer}\n"
        f"  role: {mb.bullet.role}\n"
        f"  source_text: {mb.bullet.text}\n"
        f"  emphasis: {mb.emphasis}\n"
        f"  satisfies_requirements: {mb.satisfied_requirements}"
        for mb in matched_bullets
    )
    user = (
        f"Source bullets, in fixed order — do not reorder, add, or drop any:\n\n{groups_text}"
    )

    result = call_structured(
        system=REWRITE_SYSTEM_PROMPT,
        user=user,
        schema=TailoredResume,
        tool_name="record_tailored_resume",
    )

    # Enforce order/identity fidelity in code rather than trusting the prompt alone:
    # rebuild the output in the exact input order, falling back to the unmodified
    # source bullet if the model dropped or mismatched an id.
    rewritten_by_id = {b.bullet_id: b for b in result.bullets}
    fixed_bullets = [
        rewritten_by_id.get(
            mb.bullet.id,
            RewrittenBullet(
                bullet_id=mb.bullet.id,
                employer=mb.bullet.employer,
                role=mb.bullet.role,
                text=mb.bullet.text,
            ),
        )
        for mb in matched_bullets
    ]
    return TailoredResume(bullets=fixed_bullets)
