#!/usr/bin/env python3
"""Phase-1 cleanup for enriched markdown files.

Removes:
- image-only markdown lines
- "Get Directions" lines/sections and bing maps directions links
- markdown sections whose body is only N/A (or now-empty after image/directions removal)

Keeps:
- regular links
- social proof and posts
"""

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path


IMAGE_LINE_RE = re.compile(r"^\s*(?:[-*]\s+)?!\[[^\]]*\]\([^)]*\)\s*$")
HEADING_RE = re.compile(r"^(#{1,6})\s+.+$")
GET_DIRECTIONS_HEADING_RE = re.compile(r"^\s*#{1,6}\s*get\s+directions\s*$", re.IGNORECASE)
COLD_JOIN_URL_RE = re.compile(r"https://www\.linkedin\.com/signup/cold-join(?:\?\S*)?", re.IGNORECASE)
NA_MARKDOWN_LINK_RE = re.compile(r"^\s*\[\s*n/?a\s*\]\(\s*n/?a\s*\)\s*$", re.IGNORECASE)
URL_TRACKING_PARAM_RE = re.compile(r"\?trk=[^)\]\s]+", re.IGNORECASE)
FOLLOWERS_LINE_RE = re.compile(
    r"^\s*(?:#{1,6}\s*)?\d{1,3}(?:,\d{3})*(?:\.\d+)?\s*[kKmM]?\s+followers\s*$",
    re.IGNORECASE,
)
PROFILE_FOLLOWERS_LINE_RE = re.compile(
    r"^\s*(?:#{1,6}\s*)?[^\n]{1,120}[•\-]\s*\d{1,3}(?:,\d{3})*(?:\.\d+)?\s*[kKmM]?\s+followers\s*$",
    re.IGNORECASE,
)

BLOCK_HEADING_PATTERNS = [
    re.compile(r"^people\s+also\s+viewed$", re.IGNORECASE),
    re.compile(r"^media$", re.IGNORECASE),
    re.compile(r"^additional$", re.IGNORECASE),
    re.compile(r"^sign\s+in\s+to\s+see\s+who\s+you\s+already\s+know(?:\s+at\s+.*)?$", re.IGNORECASE),
    re.compile(r"^corporate\s+associate\s+jobs$", re.IGNORECASE),
    re.compile(r"^linkedin\s+respects\s+your\s+privacy$", re.IGNORECASE),
    re.compile(r"^join\s+now\s+to\s+see\s+who\s+you\s+already\s+know(?:\s+at\s+.*)?$", re.IGNORECASE),
    re.compile(r"^more\s+from\s+this\s+author$", re.IGNORECASE),
]


def heading_text(line: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"^\s*#{1,6}\s*", "", line)).strip()


def should_drop_heading_block(line: str) -> bool:
    text = heading_text(line)
    return any(pattern.match(text) for pattern in BLOCK_HEADING_PATTERNS)


INLINE_BLOCK_MARKERS = [
    "## People Also Viewed",
    "## Media",
    "## Additional",
    "## Sign in to see who you already know",
    "### Corporate Associate jobs",
    "## LinkedIn respects your privacy",
    "## Join now to see who you already know",
    "## More from this author",
]


POLICY_TRASH_PATTERNS = [
    re.compile(r"linkedin\s+and\s+3rd\s+parties\s+use\s+essential\s+and\s+non-essential\s+cookies", re.IGNORECASE),
    re.compile(r"select\s+accept\s+to\s+consent\s+or\s+reject\s+to\s+decline\s+non-essential\s+cookies", re.IGNORECASE),
    re.compile(r"by\s+clicking\s+continue\s+to\s+join\s+or\s+sign\s+in", re.IGNORECASE),
    re.compile(r"agree\s*&\s*join\s+linkedin", re.IGNORECASE),
    re.compile(r"\[cookie\s+policy\]\(/legal/cookie-policy", re.IGNORECASE),
    re.compile(r"\[privacy\s+policy\]\(/legal/privacy-policy", re.IGNORECASE),
    re.compile(r"\[user\s+agreement\]\(/legal/user-agreement", re.IGNORECASE),
    re.compile(r"linkedin\.com/legal/cookie-policy", re.IGNORECASE),
    re.compile(r"linkedin\.com/legal/privacy-policy", re.IGNORECASE),
]

LOW_VALUE_LINE_PATTERNS = [
    re.compile(r"^\s*view\s+post\s*$", re.IGNORECASE),
    re.compile(r"^\s*activity\s+image\s*$", re.IGNORECASE),
    re.compile(r"^\s*\.\.\.more\s*$", re.IGNORECASE),
    re.compile(r"^\s*play\s+video\s*$", re.IGNORECASE),
    re.compile(r"^\s*video\s+player\s+is\s+loading\.?\s*$", re.IGNORECASE),
    re.compile(r"^\s*loaded:\s*0%\s*$", re.IGNORECASE),
    re.compile(r"^\s*0:00\s*$", re.IGNORECASE),
    re.compile(r"^\s*play\s+back\s+to\s+start\s*$", re.IGNORECASE),
    re.compile(r"^\s*stream\s+type\s+live\s*$", re.IGNORECASE),
    re.compile(r"^\s*current\s+time\s+0:00\s*$", re.IGNORECASE),
    re.compile(r"^\s*/\s*$"),
    re.compile(r"^\s*duration-:-\s*$", re.IGNORECASE),
    re.compile(r"^\s*1x\s*$", re.IGNORECASE),
    re.compile(r"^\s*playback\s+rate\s*$", re.IGNORECASE),
    re.compile(r"^\s*show\s+captions\s*$", re.IGNORECASE),
    re.compile(r"^\s*mute\s*$", re.IGNORECASE),
    re.compile(r"^\s*fullscreen\s*$", re.IGNORECASE),
    re.compile(r"^\s*no\s+alternative\s+text\s+description\s+for\s+this\s+image\s*$", re.IGNORECASE),
    re.compile(r"^\s*\[\.\.\.\]\(\s*n/?a\s*\)\s*$", re.IGNORECASE),
    re.compile(r"^\s*already\s+on\s+linkedin\?\s*(?:\[?sign\s*in\]?[^\n]*)?$", re.IGNORECASE),
    re.compile(r"^\s*new\s+to\s+linkedin\?\s+join\s+now\s+or\s*$", re.IGNORECASE),
    re.compile(r"^\s*linkedin\s+is\s+better\s+on\s+the\s+app\s*$", re.IGNORECASE),
    re.compile(r"^\s*linkedin\s*$", re.IGNORECASE),
    re.compile(r"^\s*or\s*$", re.IGNORECASE),
    re.compile(r"^\s*view\s+profile\s+for\s+.*$", re.IGNORECASE),
    re.compile(r"^\s*more\s+from\s+this\s+author\s*$", re.IGNORECASE),
    re.compile(r"^\s*don[’']?t\s+have\s+the\s+app\?\s+get\s+it\s+in\s+the\s+microsoft\s+store\.?\s*$", re.IGNORECASE),
]

INLINE_PHRASE_PATTERNS = [
    re.compile(r"\bdon[’']?t\s+have\s+the\s+app\?\s+get\s+it\s+in\s+the\s+microsoft\s+store\.?", re.IGNORECASE),
    re.compile(r"\balready\s+on\s+linkedin\?\s*sign\s+in\b", re.IGNORECASE),
    re.compile(r"\bnew\s+to\s+linkedin\?\s+join\s+now\s+or\b", re.IGNORECASE),
]


def is_policy_trash_line(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    return any(p.search(s) for p in POLICY_TRASH_PATTERNS)


def is_low_value_line(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    # Normalize unicode spacing and zero-width chars before matching.
    s_norm = s.replace("\u200b", "").replace("\ufeff", "")
    s_norm = re.sub(r"\s+", " ", s_norm).strip()

    if FOLLOWERS_LINE_RE.match(s_norm) or PROFILE_FOLLOWERS_LINE_RE.match(s_norm):
        return True
    return any(p.match(s_norm) for p in LOW_VALUE_LINE_PATTERNS)


def trim_inline_block_marker(line: str) -> tuple[str, bool]:
    """Trim inline block markers and everything after them in a line."""
    idx = -1
    for marker in INLINE_BLOCK_MARKERS:
        marker_idx = line.find(marker)
        if marker_idx >= 0 and (idx == -1 or marker_idx < idx):
            idx = marker_idx
    if idx < 0:
        return line, False
    return line[:idx].rstrip(), True


def is_na_line(line: str) -> bool:
    s = line.strip().lower()
    if not s:
        return True
    if s in {"n/a", "- n/a", "* n/a", "n/a.", "none", "unknown"}:
        return True
    return False


def is_get_directions_line(line: str) -> bool:
    s = line.strip().lower()
    if "get directions" in s:
        return True
    if "directions](" in s and "bing.com/maps" in s:
        return True
    return False


def clean_lines(lines: list[str]) -> tuple[list[str], dict[str, int]]:
    stats = {
        "removed_image_lines": 0,
        "removed_direction_lines": 0,
        "removed_na_sections": 0,
        "removed_signup_urls": 0,
        "removed_named_blocks": 0,
        "trimmed_inline_blocks": 0,
        "removed_na_link_lines": 0,
        "removed_policy_lines": 0,
        "removed_low_value_lines": 0,
        "stripped_trk_params": 0,
        "removed_ellipsis_fragments": 0,
        "removed_inline_phrases": 0,
    }

    # First pass: remove explicit image and direction lines.
    first_pass: list[str] = []
    for line in lines:
        line, trimmed = trim_inline_block_marker(line)
        if trimmed:
            stats["trimmed_inline_blocks"] += 1

        if IMAGE_LINE_RE.match(line):
            stats["removed_image_lines"] += 1
            continue
        if NA_MARKDOWN_LINK_RE.match(line):
            stats["removed_na_link_lines"] += 1
            continue
        if is_get_directions_line(line):
            stats["removed_direction_lines"] += 1
            continue
        if is_policy_trash_line(line):
            stats["removed_policy_lines"] += 1
            continue
        if is_low_value_line(line):
            stats["removed_low_value_lines"] += 1
            continue

        for pattern in INLINE_PHRASE_PATTERNS:
            line, removed = pattern.subn("", line)
            if removed:
                stats["removed_inline_phrases"] += removed

        # Remove common Tavily truncation fragment while keeping surrounding text.
        if "[...]" in line:
            line = line.replace(" [...] ", " ").replace("[...] ", "").replace(" [...]", "")
            stats["removed_ellipsis_fragments"] += 1

        line, trk_removed = URL_TRACKING_PARAM_RE.subn("", line)
        if trk_removed:
            stats["stripped_trk_params"] += trk_removed

        line, replaced = COLD_JOIN_URL_RE.subn("", line)
        if replaced:
            stats["removed_signup_urls"] += replaced
        if not line.strip():
            continue
        first_pass.append(line)

    # Second pass: remove whole "Get Directions" heading blocks.
    second_pass: list[str] = []
    i = 0
    while i < len(first_pass):
        line = first_pass[i]
        if GET_DIRECTIONS_HEADING_RE.match(line):
            i += 1
            while i < len(first_pass) and not HEADING_RE.match(first_pass[i]):
                i += 1
            continue
        if HEADING_RE.match(line) and should_drop_heading_block(line):
            stats["removed_named_blocks"] += 1
            i += 1
            while i < len(first_pass) and not HEADING_RE.match(first_pass[i]):
                i += 1
            continue
        second_pass.append(line)
        i += 1

    # Third pass: drop heading sections whose body is only N/A/blank.
    out: list[str] = []
    i = 0
    while i < len(second_pass):
        line = second_pass[i]
        if not HEADING_RE.match(line):
            out.append(line)
            i += 1
            continue

        heading = line
        body: list[str] = []
        i += 1
        while i < len(second_pass) and not HEADING_RE.match(second_pass[i]):
            body.append(second_pass[i])
            i += 1

        meaningful = False
        for body_line in body:
            if is_na_line(body_line):
                continue
            # Images/directions were already removed above, but keep this guard.
            if IMAGE_LINE_RE.match(body_line) or is_get_directions_line(body_line):
                continue
            meaningful = True
            break

        if meaningful:
            out.append(heading)
            out.extend(body)
        else:
            stats["removed_na_sections"] += 1

    # Final normalization: collapse 3+ blank lines to max 2.
    normalized: list[str] = []
    blank_run = 0
    for line in out:
        if line.strip() == "":
            blank_run += 1
        else:
            blank_run = 0
        if blank_run <= 2:
            normalized.append(line)

    # Trim leading/trailing blank lines.
    while normalized and normalized[0].strip() == "":
        normalized.pop(0)
    while normalized and normalized[-1].strip() == "":
        normalized.pop()

    if normalized:
        normalized.append("")
    return normalized, stats


def process_file(path: Path) -> dict[str, int]:
    original = path.read_text(encoding="utf-8", errors="ignore")
    lines = original.splitlines()
    cleaned_lines, stats = clean_lines(lines)
    cleaned = "\n".join(cleaned_lines)

    if cleaned != original:
        path.write_text(cleaned, encoding="utf-8")
        stats["changed"] = 1
    else:
        stats["changed"] = 0
    return stats


def process_dir(dir_path: Path, batch_size: int) -> dict[str, int]:
    files = sorted(dir_path.glob("*.md"))
    total_stats = {
        "files": len(files),
        "changed": 0,
        "removed_image_lines": 0,
        "removed_direction_lines": 0,
        "removed_na_sections": 0,
        "removed_signup_urls": 0,
        "removed_named_blocks": 0,
        "trimmed_inline_blocks": 0,
        "removed_na_link_lines": 0,
        "removed_policy_lines": 0,
        "removed_low_value_lines": 0,
        "stripped_trk_params": 0,
        "removed_ellipsis_fragments": 0,
        "removed_inline_phrases": 0,
    }
    if not files:
        return total_stats

    batches = math.ceil(len(files) / batch_size)
    for batch_idx in range(batches):
        start = batch_idx * batch_size
        end = min((batch_idx + 1) * batch_size, len(files))
        batch = files[start:end]
        print(
            f"[{dir_path.name}] batch {batch_idx + 1}/{batches}: processing files {start + 1}-{end}"
        )
        for file_path in batch:
            stats = process_file(file_path)
            total_stats["changed"] += stats["changed"]
            total_stats["removed_image_lines"] += stats["removed_image_lines"]
            total_stats["removed_direction_lines"] += stats["removed_direction_lines"]
            total_stats["removed_na_sections"] += stats["removed_na_sections"]
            total_stats["removed_signup_urls"] += stats["removed_signup_urls"]
            total_stats["removed_named_blocks"] += stats["removed_named_blocks"]
            total_stats["trimmed_inline_blocks"] += stats["trimmed_inline_blocks"]
            total_stats["removed_na_link_lines"] += stats["removed_na_link_lines"]
            total_stats["removed_policy_lines"] += stats["removed_policy_lines"]
            total_stats["removed_low_value_lines"] += stats["removed_low_value_lines"]
            total_stats["stripped_trk_params"] += stats["stripped_trk_params"]
            total_stats["removed_ellipsis_fragments"] += stats["removed_ellipsis_fragments"]
            total_stats["removed_inline_phrases"] += stats["removed_inline_phrases"]

    return total_stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase-1 cleanup for enriched markdown")
    parser.add_argument(
        "--companies-dir",
        default="data/enriched/companies",
        help="Path to enriched companies markdown dir",
    )
    parser.add_argument(
        "--connections-dir",
        default="data/enriched/connections",
        help="Path to enriched connections markdown dir",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=200,
        help="How many files to process per batch",
    )
    args = parser.parse_args()

    companies_dir = Path(args.companies_dir)
    connections_dir = Path(args.connections_dir)
    if not companies_dir.exists() or not connections_dir.exists():
        raise SystemExit("Input directories not found")

    companies_stats = process_dir(companies_dir, args.batch_size)
    connections_stats = process_dir(connections_dir, args.batch_size)

    print("\nCleanup summary")
    print("-" * 60)
    for label, stats in (("companies", companies_stats), ("connections", connections_stats)):
        print(f"{label}: files={stats['files']} changed={stats['changed']}")
        print(
            "  removed: "
            f"images={stats['removed_image_lines']} "
            f"directions={stats['removed_direction_lines']} "
            f"na_sections={stats['removed_na_sections']} "
            f"signup_urls={stats['removed_signup_urls']} "
            f"named_blocks={stats['removed_named_blocks']} "
            f"inline_block_trims={stats['trimmed_inline_blocks']} "
            f"na_link_lines={stats['removed_na_link_lines']} "
            f"policy_lines={stats['removed_policy_lines']} "
            f"low_value_lines={stats['removed_low_value_lines']} "
            f"trk_params={stats['stripped_trk_params']} "
            f"ellipsis={stats['removed_ellipsis_fragments']} "
            f"inline_phrases={stats['removed_inline_phrases']}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
