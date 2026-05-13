"""Utilities for cleaning noisy markdown and scoring chunk quality."""

from __future__ import annotations

import re
from dataclasses import dataclass

NOISE_MARKERS = [
    "people also viewed",
    "view post activity",
    "sign in to continue",
    "privacy policy",
    "cookie policy",
    "join now",
    "new to linkedin",
    "by clicking continue",
    "user agreement",
    "terms of service",
]


@dataclass
class CleaningStats:
    original_chars: int
    cleaned_chars: int
    removed_lines: int
    removed_noise_hits: int


@dataclass
class QualityStats:
    score: float
    alpha_ratio: float
    noise_hits: int
    unique_line_ratio: float


def _normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip().lower())


def clean_tavily_markdown(text: str, max_lines: int = 220) -> tuple[str, CleaningStats]:
    """Remove obvious web-scrape boilerplate and repeated low-value lines."""
    original_chars = len(text)
    cleaned_lines: list[str] = []
    seen_normalized: set[str] = set()
    removed_lines = 0
    removed_noise_hits = 0

    for raw_line in text.splitlines()[:max_lines]:
        line = raw_line.rstrip()
        normalized = _normalize_line(line)

        if not normalized:
            if cleaned_lines and cleaned_lines[-1] != "":
                cleaned_lines.append("")
            continue

        if any(marker in normalized for marker in NOISE_MARKERS):
            removed_lines += 1
            removed_noise_hits += 1
            continue

        if normalized in seen_normalized and len(normalized) > 25:
            removed_lines += 1
            continue

        seen_normalized.add(normalized)
        cleaned_lines.append(line)

    cleaned_text = "\n".join(cleaned_lines).strip()
    if not cleaned_text:
        cleaned_text = text.strip()

    stats = CleaningStats(
        original_chars=original_chars,
        cleaned_chars=len(cleaned_text),
        removed_lines=removed_lines,
        removed_noise_hits=removed_noise_hits,
    )
    return cleaned_text, stats


def score_text_quality(text: str) -> QualityStats:
    """Compute a lightweight quality score for filtering bad chunks."""
    if not text:
        return QualityStats(score=0.0, alpha_ratio=0.0, noise_hits=0, unique_line_ratio=0.0)

    lowered = text.lower()
    noise_hits = sum(1 for marker in NOISE_MARKERS if marker in lowered)

    alpha_chars = sum(1 for ch in text if ch.isalpha())
    alpha_ratio = alpha_chars / max(1, len(text))

    lines = [ln.strip().lower() for ln in text.splitlines() if ln.strip()]
    unique_line_ratio = (len(set(lines)) / len(lines)) if lines else 0.0

    score = (
        min(1.0, len(text) / 800.0) * 0.45
        + min(1.0, alpha_ratio * 2.0) * 0.30
        + unique_line_ratio * 0.25
        - min(0.5, noise_hits * 0.06)
    )
    score = max(0.0, min(1.0, score))

    return QualityStats(
        score=score,
        alpha_ratio=alpha_ratio,
        noise_hits=noise_hits,
        unique_line_ratio=unique_line_ratio,
    )
