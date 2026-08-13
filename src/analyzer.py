"""
AI analyzer skeleton.

The production version should read unanalyzed rows from SQLite, call the AI model,
validate JSON, and update news_items with structured fields.
"""

import bootstrap  # noqa: F401
from pathlib import Path


PROMPT_PATH = Path(__file__).with_name("analysis_prompt.md")


def build_analysis_prompt(raw_text: str, article_text: str | None = None) -> str:
    instructions = PROMPT_PATH.read_text(encoding="utf-8")
    body = article_text or raw_text

    return f"{instructions}\n\nNews item:\n{body}"
