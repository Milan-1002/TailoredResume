from llm import call_structured
from models import ParsedJD
from prompts import JD_PARSING_SYSTEM_PROMPT


def parse_jd(jd_text: str) -> ParsedJD:
    return call_structured(
        system=JD_PARSING_SYSTEM_PROMPT,
        user=f"Job description:\n\n{jd_text}",
        schema=ParsedJD,
        tool_name="record_parsed_jd",
    )
