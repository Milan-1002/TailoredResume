import asyncio
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

import db
from docx_export import OUTPUT_DIR, export_tailored_docx
from gap_fill import generate_keyword_injections
from match import match_all
from models import (
    FinalizeRequest,
    FinalizeResponse,
    ProposedChange,
    ResumeBullet,
    RewrittenBullet,
    TailorAnalyzeResponse,
    TailoredResume,
)
from parse_jd import parse_jd
from parse_resume import parse_resume
from pdf_export import export_pdf
from rewrite import rewrite_bullets, select_bullets_for_rewrite
from score import build_score_report
from tech_swap import generate_tech_swaps

app = FastAPI(title="Resume Tailoring Agent API")

app.add_middleware(
    CORSMiddleware,
    # Vite falls back to the next free port (5174, 5175, ...) whenever 5173 is
    # already taken by another project on the machine, and binds to 127.0.0.1
    # rather than localhost (see vite.config.ts), so match either host and any port.
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TailorAnalyzeRequest(BaseModel):
    jd_text: str


def _save_upload_to_tmp(filename: str, content: bytes) -> Path:
    suffix = Path(filename).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        return Path(tmp.name)


@app.post("/api/resume/upload")
async def upload_resume(file: UploadFile):
    content = await file.read()
    tmp_path = _save_upload_to_tmp(file.filename or "resume", content)

    bullets = parse_resume(tmp_path)
    db.save_bullets(bullets)

    has_docx = tmp_path.suffix.lower() == ".docx"
    if has_docx:
        db.save_original_docx(tmp_path)

    return {"bullets": [b.model_dump() for b in bullets], "has_docx": has_docx}


@app.get("/api/resume/bullets")
async def get_resume_bullets() -> list[ResumeBullet]:
    return db.load_bullets()


@app.post("/api/tailor/analyze")
async def tailor_analyze(req: TailorAnalyzeRequest) -> TailorAnalyzeResponse:
    bullets = db.load_bullets()
    if not bullets:
        raise HTTPException(400, "No master resume found. Upload a resume first.")

    parsed_jd = parse_jd(req.jd_text)
    match_results = match_all(parsed_jd.requirements, bullets)
    report = build_score_report(parsed_jd, bullets, match_results)

    used_bullet_ids: set[str] = set()
    proposed_changes: list[ProposedChange] = []

    # Step 1: tech swap, restricted to the most recent roles, hard_skill gaps only.
    tech_swaps = generate_tech_swaps(parsed_jd, report, bullets)
    for change in tech_swaps:
        used_bullet_ids.add(change.bullet_id)
    proposed_changes.extend(tech_swaps)

    # Step 2: existing conservative rewrite, filtered to exclude bullets used in step 1.
    remaining_bullets = [b for b in bullets if b.id not in used_bullet_ids]
    matched_for_rewrite = select_bullets_for_rewrite(remaining_bullets, match_results)
    satisfied_by_bullet_id = {
        mb.bullet.id: mb.satisfied_requirements for mb in matched_for_rewrite
    }
    tailored = rewrite_bullets(matched_for_rewrite)
    bullets_by_id = {b.id: b for b in bullets}

    for rb in tailored.bullets:
        source = bullets_by_id.get(rb.bullet_id)
        if source is None:
            continue
        if rb.text.strip() == source.text.strip():
            continue

        satisfied = satisfied_by_bullet_id.get(rb.bullet_id, [])
        proposed_changes.append(
            ProposedChange(
                id=f"{rb.bullet_id}__rewrite",
                bullet_id=rb.bullet_id,
                employer=rb.employer,
                role=rb.role,
                change_type="rewrite",
                original_text=source.text,
                proposed_text=rb.text,
                rationale="Rewritten to foreground relevance to matched JD requirement(s), using only facts already in the bullet.",
                related_requirement="; ".join(satisfied) if satisfied else None,
                requires_confirmation=False,
                confirmation_prompt=None,
            )
        )
        used_bullet_ids.add(rb.bullet_id)

    # Step 3: keyword-gap injection for total-evidence-gap requirements, must_have first.
    gap_changes = generate_keyword_injections(parsed_jd, report, bullets, used_bullet_ids)
    proposed_changes.extend(gap_changes)

    return TailorAnalyzeResponse(
        parsed_jd=parsed_jd,
        report=report,
        proposed_changes=proposed_changes,
    )


@app.post("/api/tailor/finalize")
async def tailor_finalize(req: FinalizeRequest) -> FinalizeResponse:
    bullets = db.load_bullets()
    bullets_by_id = {b.id: b for b in bullets}

    tailored_bullets: list[RewrittenBullet] = []
    for fb in req.bullets:
        source = bullets_by_id.get(fb.bullet_id)
        if source is None:
            continue
        tailored_bullets.append(
            RewrittenBullet(
                bullet_id=fb.bullet_id,
                employer=source.employer,
                role=source.role,
                text=fb.text,
            )
        )
    tailored = TailoredResume(bullets=tailored_bullets)

    original_docx_path = db.load_original_docx_path()
    if original_docx_path is None:
        return FinalizeResponse(
            docx_url=None,
            pdf_url=None,
            edited_count=0,
            skipped_count=len(tailored_bullets),
        )

    export = export_tailored_docx(tailored, bullets, original_docx_path)

    pdf_url: str | None = None
    pdf_path = OUTPUT_DIR / "tailored_resume.pdf"
    try:
        await asyncio.to_thread(export_pdf, export.path, pdf_path)
        # docx2pdf drives Word via AppleScript and can return without raising even when
        # no file was actually produced (e.g. no GUI session available to automate) —
        # only report a pdf_url if the file genuinely landed on disk.
        if pdf_path.exists():
            pdf_url = f"/api/download/{pdf_path.name}"
    except Exception:
        # PDF conversion drives a local GUI app (Word) and can fail for environment
        # reasons; don't fail the whole finalize request over it — the docx is still valid.
        pdf_url = None

    return FinalizeResponse(
        docx_url=f"/api/download/{export.path.name}",
        pdf_url=pdf_url,
        edited_count=export.edited_count,
        skipped_count=export.skipped_count,
    )


@app.get("/api/download/{filename}")
async def download_file(filename: str):
    if "/" in filename or "\\" in filename or filename in ("..", ".") or Path(filename).name != filename:
        raise HTTPException(400, "Invalid filename.")

    path = OUTPUT_DIR / filename
    if not path.exists() or not path.is_file():
        raise HTTPException(404, "File not found.")

    return FileResponse(path)
