from models import JDRequirement, MatchResult, ParsedJD, ResumeBullet, ScoreReport

IMPORTANCE_WEIGHT = {"must_have": 3.0, "nice_to_have": 1.0}
MAX_COVERAGE = 2


def compute_keyword_coverage_pct(parsed_jd: ParsedJD, bullets: list[ResumeBullet]) -> float:
    resume_skills = {s.lower() for b in bullets for s in b.skills}

    jd_terms: set[str] = set()
    for req in parsed_jd.requirements:
        jd_terms.update(s.lower() for s in req.implied_skills)
        req_text_lower = req.text.lower()
        jd_terms.update(skill for skill in resume_skills if skill in req_text_lower)

    if not jd_terms:
        return 0.0

    matched = jd_terms & resume_skills
    return round(100 * len(matched) / len(jd_terms), 1)


def compute_substantive_fit_score(
    requirements: list[JDRequirement], match_results: list[MatchResult]
) -> float:
    weight_by_req = {req.text: IMPORTANCE_WEIGHT[req.importance] for req in requirements}

    weighted_sum = 0.0
    total_possible = 0.0
    for result in match_results:
        weight = weight_by_req.get(result.requirement, IMPORTANCE_WEIGHT["nice_to_have"])
        weighted_sum += weight * result.coverage
        total_possible += weight * MAX_COVERAGE

    if total_possible == 0:
        return 0.0
    return round(100 * weighted_sum / total_possible, 1)


def compute_must_have_gaps(
    requirements: list[JDRequirement], match_results: list[MatchResult]
) -> list[str]:
    must_have_texts = {req.text for req in requirements if req.importance == "must_have"}
    return [
        result.requirement
        for result in match_results
        if result.requirement in must_have_texts and result.coverage == 0
    ]


def build_score_report(
    parsed_jd: ParsedJD, bullets: list[ResumeBullet], match_results: list[MatchResult]
) -> ScoreReport:
    return ScoreReport(
        keyword_coverage_pct=compute_keyword_coverage_pct(parsed_jd, bullets),
        substantive_fit_score=compute_substantive_fit_score(parsed_jd.requirements, match_results),
        must_have_gaps=compute_must_have_gaps(parsed_jd.requirements, match_results),
        per_requirement=match_results,
    )
