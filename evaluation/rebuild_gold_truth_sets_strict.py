"""Strictly rebuild gold truth sets from enriched markdown files.

Rules implemented per user request:
- Search by each theme keyword across data/enriched/companies and data/enriched/connections.
- Read whole matched files and score relevance by section.
- Keep only entities where theme appears primary.
- Exclude secondary/weak thematic mentions.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
ENRICHED_CONNECTIONS = REPO_ROOT / "data" / "enriched" / "connections"
ENRICHED_COMPANIES = REPO_ROOT / "data" / "enriched" / "companies"
CURRENT_GOLD = REPO_ROOT / "evaluation" / "gold_truth_sets.json"


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _extract_line(content: str, label: str) -> str:
    pattern = rf"^\*\*{re.escape(label)}:\*\*\s*(.+)$"
    m = re.search(pattern, content, flags=re.MULTILINE | re.IGNORECASE)
    return m.group(1).strip() if m else ""


def _extract_section(content: str, heading: str) -> str:
    pattern = rf"^##\s+{re.escape(heading)}\s*$\n(.+?)(?=^##\s+|\Z)"
    m = re.search(pattern, content, flags=re.MULTILINE | re.DOTALL)
    return m.group(1).strip() if m else ""


def _keyword_hits(text: str, keywords: list[str]) -> tuple[int, set[str]]:
    lowered = _norm(text)
    hits: set[str] = set()
    for kw in keywords:
        k = _norm(kw)
        if not k:
            continue
        if re.search(rf"\b{re.escape(k)}\b", lowered):
            hits.add(k)
    return len(hits), hits


def _weighted_theme_score_company(content: str, keywords: list[str]) -> tuple[float, set[str]]:
    name = _extract_line(content, "Company Name")
    industry = _extract_section(content, "Industry")
    overview = _extract_section(content, "About Us/Overview")
    specialties = _extract_section(content, "Specialties")
    full_text = content

    s_name, h1 = _keyword_hits(name, keywords)
    s_industry, h2 = _keyword_hits(industry, keywords)
    s_overview, h3 = _keyword_hits(overview, keywords)
    s_specs, h4 = _keyword_hits(specialties, keywords)
    s_full, h5 = _keyword_hits(full_text, keywords)

    # Primary-signal weighting: industry/overview/specialties are strongest.
    score = (
        (s_name * 2.0)
        + (s_industry * 4.0)
        + (s_overview * 3.5)
        + (s_specs * 3.0)
        + (s_full * 0.4)
    )
    return score, set().union(h1, h2, h3, h4, h5)


def _weighted_theme_score_connection(content: str, keywords: list[str]) -> tuple[float, set[str]]:
    name = _extract_line(content, "Name and Surname")
    company = _extract_line(content, "Current Company")
    position = _extract_line(content, "Position")
    summary = _extract_section(content, "Professional Summary")
    full_text = content

    s_name, h1 = _keyword_hits(name, keywords)
    s_company, h2 = _keyword_hits(company, keywords)
    s_position, h3 = _keyword_hits(position, keywords)
    s_summary, h4 = _keyword_hits(summary, keywords)
    s_full, h5 = _keyword_hits(full_text, keywords)

    # Primary-signal weighting: position/summary/company are strongest.
    score = (
        (s_name * 1.0)
        + (s_company * 2.5)
        + (s_position * 3.5)
        + (s_summary * 4.0)
        + (s_full * 0.4)
    )
    return score, set().union(h1, h2, h3, h4, h5)


def _load_themes() -> dict[str, dict[str, Any]]:
    payload = json.loads(CURRENT_GOLD.read_text(encoding="utf-8"))
    return payload.get("themes", {})


def _read_companies() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for md in sorted(ENRICHED_COMPANIES.glob("*.md")):
        content = md.read_text(encoding="utf-8", errors="ignore")
        name = _extract_line(content, "Company Name") or md.stem
        rows.append({"name": name, "path": str(md), "content": content})
    return rows


def _read_connections() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for md in sorted(ENRICHED_CONNECTIONS.glob("*.md")):
        content = md.read_text(encoding="utf-8", errors="ignore")
        name = _extract_line(content, "Name and Surname") or md.stem
        rows.append({"name": name, "path": str(md), "content": content})
    return rows


def _assign_primary(
    entity_content: str,
    theme_keywords: dict[str, list[str]],
    is_company: bool,
) -> dict[str, Any]:
    scorer = _weighted_theme_score_company if is_company else _weighted_theme_score_connection

    per_theme: dict[str, tuple[float, set[str]]] = {}
    for theme_key, kws in theme_keywords.items():
        per_theme[theme_key] = scorer(entity_content, kws)

    ranked = sorted(
        ((k, v[0], v[1]) for k, v in per_theme.items()),
        key=lambda x: x[1],
        reverse=True,
    )

    best_theme, best_score, best_hits = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0.0

    # Primary gating:
    # - at least 2 keyword hits
    # - meaningful score floor
    # - dominance over second-best theme
    is_primary = (
        len(best_hits) >= 2
        and best_score >= 8.0
        and (best_score >= second_score * 1.25)
    )

    return {
        "theme": best_theme,
        "best_score": round(best_score, 3),
        "second_score": round(second_score, 3),
        "hits": sorted(best_hits),
        "is_primary": is_primary,
    }


def rebuild(top_n: int = 15) -> dict[str, Any]:
    source_themes = _load_themes()
    theme_keywords = {
        theme: [str(k).strip() for k in data.get("keywords", []) if str(k).strip()]
        for theme, data in source_themes.items()
    }

    companies = _read_companies()
    connections = _read_connections()

    picked_companies: dict[str, list[tuple[str, float]]] = defaultdict(list)
    picked_connections: dict[str, list[tuple[str, float]]] = defaultdict(list)

    # Full-file read + primary classification for companies
    for row in companies:
        res = _assign_primary(row["content"], theme_keywords, is_company=True)
        if not res["is_primary"]:
            continue
        picked_companies[res["theme"]].append((row["name"], res["best_score"]))

    # Full-file read + primary classification for connections
    for row in connections:
        res = _assign_primary(row["content"], theme_keywords, is_company=False)
        if not res["is_primary"]:
            continue
        picked_connections[res["theme"]].append((row["name"], res["best_score"]))

    # Build output with dedupe + top-N by score.
    themes_out: dict[str, Any] = {}
    for theme_key, data in source_themes.items():
        label = data.get("label", theme_key)
        keywords = data.get("keywords", [])

        cands_conn = sorted(picked_connections.get(theme_key, []), key=lambda x: x[1], reverse=True)
        cands_comp = sorted(picked_companies.get(theme_key, []), key=lambda x: x[1], reverse=True)

        unique_conn = []
        seen = set()
        for name, _score in cands_conn:
            k = _norm(name)
            if not k or k in seen:
                continue
            seen.add(k)
            unique_conn.append(name)
            if len(unique_conn) >= top_n:
                break

        unique_comp = []
        seen = set()
        for name, _score in cands_comp:
            k = _norm(name)
            if not k or k in seen:
                continue
            seen.add(k)
            unique_comp.append(name)
            if len(unique_comp) >= top_n:
                break

        themes_out[theme_key] = {
            "label": label,
            "keywords": keywords,
            "connection_count": len(unique_conn),
            "company_count": len(unique_comp),
            "connections": unique_conn,
            "companies": unique_comp,
        }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "selection_threshold": top_n,
        "method": "strict_primary_full_file_keyword_classification",
        "themes": themes_out,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Strictly rebuild gold truth sets from enriched data")
    parser.add_argument("--top", type=int, default=15)
    parser.add_argument("--output", default="evaluation/gold_truth_sets.json")
    args = parser.parse_args()

    rebuilt = rebuild(top_n=args.top)

    out = REPO_ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rebuilt, indent=2, ensure_ascii=False), encoding="utf-8")

    print("Rebuilt strict gold truth sets:")
    print(f"  output: {out}")
    for theme_key, payload in rebuilt["themes"].items():
        print(
            f"  - {theme_key:<22} conn={payload['connection_count']:<2} comp={payload['company_count']:<2}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
