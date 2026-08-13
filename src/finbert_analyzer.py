"""Optional local FinBERT scoring for English financial text.

The Telegram feed is primarily Korean. ProsusAI/finbert is English-only, so the
scorer deliberately skips text that does not contain enough Latin words. The
cloud analyzer remains responsible for Korean and mixed-language interpretation.
"""

from __future__ import annotations

from dataclasses import dataclass
import re


LATIN_WORD = re.compile(r"\b[A-Za-z][A-Za-z'-]{1,}\b")
KOREAN_CHAR = re.compile(r"[\uac00-\ud7a3]")


@dataclass(frozen=True)
class FinBertResult:
    label: str
    confidence: float
    positive: float
    negative: float
    neutral: float
    model: str


def english_coverage(text: str) -> float:
    latin = len(LATIN_WORD.findall(text or ""))
    korean = len(KOREAN_CHAR.findall(text or ""))
    return latin / max(latin + korean, 1)


class FinBertAnalyzer:
    def __init__(
        self,
        model_name: str = "ProsusAI/finbert",
        minimum_english_coverage: float = 0.35,
    ) -> None:
        self.model_name = model_name
        self.minimum_english_coverage = minimum_english_coverage
        self._pipeline = None

    def eligible(self, text: str) -> bool:
        return (
            len(LATIN_WORD.findall(text or "")) >= 5
            and english_coverage(text) >= self.minimum_english_coverage
        )

    def _load(self):
        if self._pipeline is None:
            try:
                from transformers import pipeline
            except ImportError as error:
                raise RuntimeError(
                    "FinBERT is enabled but transformers is not installed. "
                    "Install requirements-finbert.txt."
                ) from error
            self._pipeline = pipeline(
                "text-classification",
                model=self.model_name,
                tokenizer=self.model_name,
                top_k=None,
                device=-1,
            )
        return self._pipeline

    def analyze(self, text: str) -> FinBertResult | None:
        if not self.eligible(text):
            return None
        predictions = self._load()(text[:4000], truncation=True)[0]
        scores = {item["label"].lower(): float(item["score"]) for item in predictions}
        label = max(scores, key=scores.get)
        return FinBertResult(
            label=label,
            confidence=scores[label],
            positive=scores.get("positive", 0.0),
            negative=scores.get("negative", 0.0),
            neutral=scores.get("neutral", 0.0),
            model=self.model_name,
        )
