from models import ParsedJD, ScoreReport, TailoredResume

COVERAGE_LABEL = {0: "0 (none)", 1: "1 (partial)", 2: "2 (strong)"}


def render_tailored_resume_md(tailored: TailoredResume) -> str:
    lines = ["# Tailored Resume", ""]

    seen_sections: list[tuple[str, str]] = []
    for b in tailored.bullets:
        key = (b.employer, b.role)
        if key not in seen_sections:
            seen_sections.append(key)

    for employer, role in seen_sections:
        lines.append(f"## {role} — {employer}")
        for b in tailored.bullets:
            if (b.employer, b.role) == (employer, role):
                lines.append(f"- {b.text}")
        lines.append("")

    return "\n".join(lines)


def render_score_report_md(report: ScoreReport, parsed_jd: ParsedJD) -> str:
    lines = [
        "# Fit Score Report",
        "",
        f"**Role:** {parsed_jd.role_title} ({parsed_jd.seniority_level})",
        "",
        "## Scores (two separate axes — never blended)",
        "",
        f"- **Keyword coverage: {report.keyword_coverage_pct}%** — "
        "the deterministic % of JD-relevant keywords/skills that literally appear "
        "somewhere in the master resume.",
        f"- **Substantive fit score: {report.substantive_fit_score}%** — "
        "a weighted average of the LLM judge's evidence strength per requirement "
        "(must-haves weighted 3x nice-to-haves); this reflects real evidence, not "
        "keyword overlap.",
        "",
        "## Must-Have Gaps (unresolved — no path to fabricate these)",
        "",
    ]
    if report.must_have_gaps:
        lines.extend(f"- {gap}" for gap in report.must_have_gaps)
    else:
        lines.append("None.")
    lines.append("")

    lines.append("## Per-Requirement Detail")
    lines.append("")
    lines.append("| Requirement | Coverage | Reasoning |")
    lines.append("|---|---|---|")
    for result in report.per_requirement:
        req = result.requirement.replace("|", "\\|")
        reasoning = result.reasoning.replace("|", "\\|")
        lines.append(f"| {req} | {COVERAGE_LABEL[result.coverage]} | {reasoning} |")

    return "\n".join(lines)
