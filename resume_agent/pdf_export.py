from pathlib import Path

from docx2pdf import convert

OUTPUT_DIR = Path(__file__).parent / "output"
DEFAULT_PDF_PATH = OUTPUT_DIR / "tailored_resume.pdf"


def export_pdf(docx_path: Path, output_path: Path = DEFAULT_PDF_PATH) -> Path:
    """Converts a .docx to .pdf by driving Microsoft Word via docx2pdf. This is a blocking,
    slow call (it drives a GUI app on macOS) — callers in async contexts (e.g. FastAPI route
    handlers) MUST invoke this via asyncio.to_thread(), never directly in an async def."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    convert(str(docx_path), str(output_path))
    return output_path
