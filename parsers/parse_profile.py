"""
parsers/parse_profile.py — Parses own LinkedIn profile CSVs into DocumentChunks.

Covers: Profile, Positions, Education, Skills, Certifications, Languages, Publications.
These are the "my identity" data — they go into the my_profile collection.
"""

import csv
from pathlib import Path
from utils.schema import DocumentChunk
from config import CSV


def _read_csv(path: Path) -> list[dict]:
    if not path.exists():
        print(f"[parse_profile] Warning: {path} not found, skipping.")
        return []
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


# ─────────────────────────────────────────────
# Profile (bio, headline, summary)
# ─────────────────────────────────────────────

def parse_profile() -> list[DocumentChunk]:
    rows = _read_csv(CSV["profile"])
    chunks = []
    for row in rows:
        parts = []
        name = f"{row.get('First Name', '')} {row.get('Last Name', '')}".strip()
        if name:        parts.append(f"Name: {name}")
        headline = row.get("Headline", "").strip()
        if headline:    parts.append(f"Headline: {headline}")
        summary = row.get("Summary", "").strip()
        if summary:     parts.append(f"Summary: {summary}")
        industry = row.get("Industry", "").strip()
        if industry:    parts.append(f"Industry: {industry}")
        location = row.get("Geo Location", "").strip()
        if location:    parts.append(f"Location: {location}")
        websites = row.get("Websites", "").strip()
        if websites:    parts.append(f"Websites: {websites}")

        if not parts:
            continue

        chunks.append(DocumentChunk(
            document="\n".join(parts),
            collection="my_profile",
            source="csv",
            type="profile_bio",
            entity_id="self::profile",
            entity_name=name or "Me",
            location=location or None,
        ))
    return chunks


# ─────────────────────────────────────────────
# Positions (work history)
# ─────────────────────────────────────────────

def parse_positions() -> list[DocumentChunk]:
    rows = _read_csv(CSV["positions"])
    chunks = []
    for i, row in enumerate(rows):
        company = row.get("Company Name", "").strip()
        title   = row.get("Title", "").strip()
        desc    = row.get("Description", "").strip()
        loc     = row.get("Location", "").strip()
        started = row.get("Started On", "").strip()
        ended   = row.get("Finished On", "").strip() or "Present"

        parts = []
        if title:   parts.append(f"Role: {title}")
        if company: parts.append(f"Company: {company}")
        if loc:     parts.append(f"Location: {loc}")
        if started: parts.append(f"Period: {started} – {ended}")
        if desc:    parts.append(f"Description: {desc}")

        if not parts:
            continue

        chunks.append(DocumentChunk(
            document="\n".join(parts),
            collection="my_profile",
            source="csv",
            type="position",
            entity_id=f"self::position::{i}",
            entity_name=f"{title} at {company}",
            company=company or None,
            location=loc or None,
            date_from=started or None,
            date_to=ended or None,
        ))
    return chunks


# ─────────────────────────────────────────────
# Education
# ─────────────────────────────────────────────

def parse_education() -> list[DocumentChunk]:
    rows = _read_csv(CSV["education"])
    chunks = []
    for i, row in enumerate(rows):
        school  = row.get("School Name", "").strip()
        degree  = row.get("Degree Name", "").strip()
        start   = row.get("Start Date", "").strip()
        end     = row.get("End Date", "").strip()
        notes   = row.get("Notes", "").strip()
        acts    = row.get("Activities", "").strip()

        parts = []
        if school:  parts.append(f"School: {school}")
        if degree:  parts.append(f"Degree: {degree}")
        if start:   parts.append(f"Period: {start} – {end or 'Present'}")
        if notes:   parts.append(f"Notes: {notes}")
        if acts:    parts.append(f"Activities: {acts}")

        if not parts:
            continue

        chunks.append(DocumentChunk(
            document="\n".join(parts),
            collection="my_profile",
            source="csv",
            type="education",
            entity_id=f"self::education::{i}",
            entity_name=f"{degree} at {school}".strip(" at"),
            date_from=start or None,
            date_to=end or None,
        ))
    return chunks


# ─────────────────────────────────────────────
# Skills (all in one chunk — usually short list)
# ─────────────────────────────────────────────

def parse_skills() -> list[DocumentChunk]:
    rows = _read_csv(CSV["skills"])
    skills = [r.get("Name", "").strip() for r in rows if r.get("Name", "").strip()]
    if not skills:
        return []
    return [DocumentChunk(
        document="Professional skills: " + ", ".join(skills),
        collection="my_profile",
        source="csv",
        type="skill",
        entity_id="self::skills",
        entity_name="Skills",
    )]


# ─────────────────────────────────────────────
# Certifications
# ─────────────────────────────────────────────

def parse_certifications() -> list[DocumentChunk]:
    rows = _read_csv(CSV["certifications"])
    chunks = []
    for i, row in enumerate(rows):
        name      = row.get("Name", "").strip()
        authority = row.get("Authority", "").strip()
        started   = row.get("Started On", "").strip()
        ended     = row.get("Finished On", "").strip()
        url       = row.get("Url", "").strip()

        parts = []
        if name:        parts.append(f"Certification: {name}")
        if authority:   parts.append(f"Issued by: {authority}")
        if started:     parts.append(f"Valid: {started}" + (f" – {ended}" if ended else ""))
        if url:         parts.append(f"URL: {url}")

        if not parts:
            continue

        chunks.append(DocumentChunk(
            document="\n".join(parts),
            collection="my_profile",
            source="csv",
            type="certification",
            entity_id=f"self::cert::{i}",
            entity_name=name,
            url=url or None,
            date_from=started or None,
            date_to=ended or None,
        ))
    return chunks


# ─────────────────────────────────────────────
# Languages
# ─────────────────────────────────────────────

def parse_languages() -> list[DocumentChunk]:
    rows = _read_csv(CSV["languages"])
    langs = []
    for r in rows:
        name = r.get("Name", "").strip()
        prof = r.get("Proficiency", "").strip()
        if name:
            langs.append(f"{name} ({prof})" if prof else name)

    if not langs:
        return []
    return [DocumentChunk(
        document="Languages spoken: " + ", ".join(langs),
        collection="my_profile",
        source="csv",
        type="language",
        entity_id="self::languages",
        entity_name="Languages",
    )]


# ─────────────────────────────────────────────
# Publications
# ─────────────────────────────────────────────

def parse_publications() -> list[DocumentChunk]:
    rows = _read_csv(CSV["publications"])
    chunks = []
    for i, row in enumerate(rows):
        name      = row.get("Name", "").strip()
        publisher = row.get("Publisher", "").strip()
        pub_date  = row.get("Published On", "").strip()
        desc      = row.get("Description", "").strip()
        url       = row.get("Url", "").strip()

        parts = []
        if name:      parts.append(f"Publication: {name}")
        if publisher: parts.append(f"Publisher: {publisher}")
        if pub_date:  parts.append(f"Published: {pub_date}")
        if desc:      parts.append(f"Description: {desc}")
        if url:       parts.append(f"URL: {url}")

        if not parts:
            continue

        chunks.append(DocumentChunk(
            document="\n".join(parts),
            collection="my_profile",
            source="csv",
            type="publication",
            entity_id=f"self::pub::{i}",
            entity_name=name,
            url=url or None,
            date_from=pub_date or None,
        ))
    return chunks


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

def parse_all_profile() -> list[DocumentChunk]:
    """Run all profile parsers and return a flat list of DocumentChunks."""
    chunks = []
    chunks.extend(parse_profile())
    chunks.extend(parse_positions())
    chunks.extend(parse_education())
    chunks.extend(parse_skills())
    chunks.extend(parse_certifications())
    chunks.extend(parse_languages())
    chunks.extend(parse_publications())
    print(f"[parse_profile] Generated {len(chunks)} chunks from profile CSVs.")
    return chunks
