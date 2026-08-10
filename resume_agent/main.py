from pathlib import Path

import click

import db
from docx_export import export_tailored_docx
from match import match_all
from parse_jd import parse_jd
from parse_resume import parse_resume, read_resume_text
from render import render_score_report_md, render_tailored_resume_md
from rewrite import rewrite_bullets, select_bullets_for_rewrite
from score import build_score_report

OUTPUT_DIR = Path(__file__).parent / "output"


@click.group()
def cli():
    pass


@cli.command("init-resume")
@click.argument("resume_path", type=click.Path(exists=True, path_type=Path))
def init_resume(resume_path: Path):
    click.echo(f"Parsing {resume_path}...")
    bullets = parse_resume(resume_path)
    db.save_bullets(bullets)
    click.echo(f"Saved {len(bullets)} bullets to {db.DB_PATH}")
    for b in bullets:
        click.echo(f"  - [{b.employer} / {b.role}] {b.text[:90]}")

    if resume_path.suffix.lower() == ".docx":
        db.save_original_docx(resume_path)
        click.echo(
            "Saved original .docx so `tailor` can produce a format-preserved "
            "tailored_resume.docx later."
        )
    else:
        click.secho(
            "Note: master resume was not a .docx, so `tailor` can only produce "
            "tailored_resume.md — it can't generate a format-preserved .docx.",
            fg="yellow",
        )


@cli.command("tailor")
@click.argument("jd_path", type=click.Path(exists=True, path_type=Path))
def tailor(jd_path: Path):
    bullets = db.load_bullets()
    if not bullets:
        raise click.ClickException(
            "No master resume found. Run `python main.py init-resume path/to/resume` first."
        )

    jd_text = read_resume_text(jd_path)
    parsed_jd = parse_jd(jd_text)

    match_results = match_all(parsed_jd.requirements, bullets)
    report = build_score_report(parsed_jd, bullets, match_results)

    if report.must_have_gaps:
        click.secho("=== MUST-HAVE GAPS (no evidence found in master resume) ===", fg="red", bold=True)
        for gap in report.must_have_gaps:
            click.secho(f"  ✗ {gap}", fg="red")
        click.echo()
    else:
        click.secho("No must-have gaps found.\n", fg="green")

    click.secho("=== Parsed Job Description ===", bold=True)
    click.echo(f"Role: {parsed_jd.role_title}")
    click.echo(f"Seniority: {parsed_jd.seniority_level}")
    click.echo(f"Requirements extracted: {len(parsed_jd.requirements)}")
    click.echo()

    click.secho("=== Per-Requirement Match Results ===", bold=True)
    for result in match_results:
        coverage_label = {0: "NO EVIDENCE", 1: "PARTIAL", 2: "STRONG"}[result.coverage]
        click.echo(f"[{coverage_label}] {result.requirement}")
        click.echo(f"    reasoning: {result.reasoning}")
    click.echo()

    matched_for_rewrite = select_bullets_for_rewrite(bullets, match_results)
    tailored = rewrite_bullets(matched_for_rewrite)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "tailored_resume.md").write_text(render_tailored_resume_md(tailored))
    (OUTPUT_DIR / "score_report.md").write_text(render_score_report_md(report, parsed_jd))
    click.secho(f"Wrote {OUTPUT_DIR / 'tailored_resume.md'}", fg="cyan")
    click.secho(f"Wrote {OUTPUT_DIR / 'score_report.md'}", fg="cyan")

    original_docx_path = db.load_original_docx_path()
    if original_docx_path is not None:
        export = export_tailored_docx(tailored, bullets, original_docx_path)
        click.secho(
            f"Wrote {export.path} ({export.edited_count} bullets updated in place, "
            f"{export.skipped_count} left unmatched/unchanged) — open it in Word and "
            "use File > Save as PDF to get your final PDF.",
            fg="cyan",
        )
    else:
        click.secho(
            "Skipped .docx export — no original .docx on file (master resume wasn't "
            "uploaded as .docx). Only tailored_resume.md was written.",
            fg="yellow",
        )


if __name__ == "__main__":
    cli()
