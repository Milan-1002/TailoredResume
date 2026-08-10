import tempfile
from pathlib import Path

import streamlit as st

import db
from docx_export import export_tailored_docx
from match import match_all
from parse_jd import parse_jd
from parse_resume import parse_resume, read_resume_text
from render import render_score_report_md, render_tailored_resume_md
from rewrite import rewrite_bullets, select_bullets_for_rewrite
from score import build_score_report

OUTPUT_DIR = Path(__file__).parent / "output"

st.set_page_config(page_title="Resume Tailoring Agent", layout="wide")
st.title("Resume Tailoring Agent")

step = st.sidebar.radio("Step", ["1. Master Resume", "2. Tailor to Job Description"])


def _save_upload_to_tmp(uploaded_file) -> Path:
    suffix = Path(uploaded_file.name).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getvalue())
        return Path(tmp.name)


if step == "1. Master Resume":
    st.header("1. Upload your master resume")
    st.caption(
        "This runs once (or whenever you update your resume). It extracts every bullet "
        "as a discrete, evidence-bearing unit and stores it in the local database."
    )

    st.caption(
        "Upload the .docx version if you want the final tailored resume to preserve your "
        "exact original formatting/layout — PDF/txt uploads only support the markdown output."
    )

    uploaded = st.file_uploader("Master resume file", type=["docx", "pdf", "txt"])
    if uploaded is not None and st.button("Parse & save resume", type="primary"):
        with st.spinner("Segmenting resume and extracting bullets..."):
            tmp_path = _save_upload_to_tmp(uploaded)
            bullets = parse_resume(tmp_path)
            db.save_bullets(bullets)
            if tmp_path.suffix.lower() == ".docx":
                db.save_original_docx(tmp_path)
        st.success(f"Saved {len(bullets)} bullets to the master resume database.")
        if tmp_path.suffix.lower() != ".docx":
            st.warning(
                "This wasn't a .docx, so tailoring will only produce a markdown resume "
                "— not a format-preserved .docx."
            )
        st.session_state["just_parsed"] = bullets

    existing = db.load_bullets()
    if existing:
        st.subheader(f"Bullets currently in database ({len(existing)})")
        for b in existing:
            with st.expander(f"[{b.employer} / {b.role}] {b.text[:80]}"):
                st.write(f"**Dates:** {b.start_date} – {b.end_date or 'present'}")
                st.write(f"**Text:** {b.text}")
                st.write(f"**Skills:** {', '.join(b.skills) if b.skills else '—'}")
                st.write(f"**Seniority signal:** {b.seniority_signal or '—'}")
                st.write(f"**Quantified outcome:** {b.quantified_outcome or '—'}")
    else:
        st.info("No bullets in the database yet — upload a resume above.")

else:
    st.header("2. Tailor to a job description")

    bullets = db.load_bullets()
    if not bullets:
        st.warning("No master resume found. Complete step 1 first.")
        st.stop()

    jd_text = ""
    jd_file = st.file_uploader("Job description file (optional)", type=["docx", "pdf", "txt"])
    if jd_file is not None:
        tmp_path = _save_upload_to_tmp(jd_file)
        jd_text = read_resume_text(tmp_path)

    jd_text = st.text_area("Or paste the job description text", value=jd_text, height=250)

    if st.button("Run tailoring pipeline", type="primary", disabled=not jd_text.strip()):
        with st.spinner("Parsing job description..."):
            parsed_jd = parse_jd(jd_text)

        with st.spinner("Matching resume bullets against each requirement..."):
            match_results = match_all(parsed_jd.requirements, bullets)

        report = build_score_report(parsed_jd, bullets, match_results)

        st.session_state["parsed_jd"] = parsed_jd
        st.session_state["report"] = report

        with st.spinner("Rewriting matched bullets for this job..."):
            matched_for_rewrite = select_bullets_for_rewrite(bullets, match_results)
            tailored = rewrite_bullets(matched_for_rewrite)
        st.session_state["tailored"] = tailored

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUTPUT_DIR / "tailored_resume.md").write_text(render_tailored_resume_md(tailored))
        (OUTPUT_DIR / "score_report.md").write_text(render_score_report_md(report, parsed_jd))

        original_docx_path = db.load_original_docx_path()
        if original_docx_path is not None:
            with st.spinner("Editing your original .docx in place..."):
                export = export_tailored_docx(tailored, bullets, original_docx_path)
            st.session_state["docx_export"] = export
        else:
            st.session_state["docx_export"] = None

    if "report" in st.session_state:
        parsed_jd = st.session_state["parsed_jd"]
        report = st.session_state["report"]
        tailored = st.session_state["tailored"]

        if report.must_have_gaps:
            st.error("**Must-have gaps — no evidence found in your master resume:**")
            for gap in report.must_have_gaps:
                st.markdown(f"- ✗ {gap}")
        else:
            st.success("No must-have gaps found.")

        st.subheader("Parsed job description")
        st.write(f"**Role:** {parsed_jd.role_title}  |  **Seniority:** {parsed_jd.seniority_level}")

        col1, col2 = st.columns(2)
        col1.metric("Keyword coverage", f"{report.keyword_coverage_pct}%")
        col1.caption("Deterministic: % of JD keywords/skills literally present in your resume.")
        col2.metric("Substantive fit score", f"{report.substantive_fit_score}%")
        col2.caption("LLM-judged evidence strength per requirement, must-haves weighted 3x.")

        st.subheader("Per-requirement match detail")
        coverage_label = {0: "0 · none", 1: "1 · partial", 2: "2 · strong"}
        st.dataframe(
            [
                {
                    "Requirement": r.requirement,
                    "Coverage": coverage_label[r.coverage],
                    "Reasoning": r.reasoning,
                }
                for r in report.per_requirement
            ],
            use_container_width=True,
            hide_index=True,
        )

        st.subheader("Tailored resume")

        docx_export = st.session_state.get("docx_export")
        if docx_export is not None:
            st.success(
                f"Edited your original .docx in place — {docx_export.edited_count} bullets "
                f"updated, {docx_export.skipped_count} left unchanged/unmatched. Same fonts, "
                "spacing, and layout as your original file. Open it in Word and use "
                "File > Save as PDF for a final PDF."
            )
            st.download_button(
                "Download tailored_resume.docx (format-preserved)",
                docx_export.path.read_bytes(),
                file_name="tailored_resume.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                type="primary",
            )
        else:
            st.info(
                "Your master resume wasn't uploaded as .docx, so only a markdown version "
                "is available below — re-upload as .docx in Step 1 for a format-preserved "
                "Word file instead."
            )

        st.markdown(render_tailored_resume_md(tailored))

        dl1, dl2 = st.columns(2)
        dl1.download_button(
            "Download tailored_resume.md",
            render_tailored_resume_md(tailored),
            file_name="tailored_resume.md",
        )
        dl2.download_button(
            "Download score_report.md",
            render_score_report_md(report, parsed_jd),
            file_name="score_report.md",
        )
