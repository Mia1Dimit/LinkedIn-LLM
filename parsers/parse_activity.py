"""
parsers/parse_activity.py — Parses job-related CSVs and activity data.

Covers: Job Applications, Saved Jobs, Saved Job Alerts,
        Job Applicant Saved Answers, All Likes / Shares.
"""

import csv
import json
from pathlib import Path
from utils.schema import DocumentChunk
from config import CSV


def _read_csv(path: Path) -> list[dict]:
    if not path.exists():
        print(f"[parse_activity] Warning: {path} not found, skipping.")
        return []
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


# ─────────────────────────────────────────────
# Job Applications
# ─────────────────────────────────────────────

def parse_job_applications() -> list[DocumentChunk]:
    rows = _read_csv(CSV["job_applications"])
    chunks = []
    for i, row in enumerate(rows):
        date    = row.get("Application Date", "").strip()
        company = row.get("Company Name", "").strip()
        title   = row.get("Job Title", "").strip()
        url     = row.get("Job Url", "").strip()
        resume  = row.get("Resume Name", "").strip()
        qa      = row.get("Question And Answers", "").strip()

        parts = []
        if title:   parts.append(f"Applied for: {title}")
        if company: parts.append(f"Company: {company}")
        if date:    parts.append(f"Applied on: {date}")
        if resume:  parts.append(f"Resume used: {resume}")
        if url:     parts.append(f"Job URL: {url}")
        if qa:      parts.append(f"Application Q&A:\n{qa}")

        if not parts:
            continue

        chunks.append(DocumentChunk(
            document="\n".join(parts),
            collection="jobs",
            source="csv",
            type="job_application",
            entity_id=f"job_application::{i}",
            entity_name=f"{title} at {company}".strip(" at"),
            company=company or None,
            url=url or None,
            date_from=date or None,
        ))
    print(f"[parse_activity] {len(chunks)} job application chunks.")
    return chunks


# ─────────────────────────────────────────────
# Saved Jobs
# ─────────────────────────────────────────────

def parse_saved_jobs() -> list[DocumentChunk]:
    rows = _read_csv(CSV["saved_jobs"])
    chunks = []
    for i, row in enumerate(rows):
        saved_date = row.get("Saved Date", "").strip()
        url        = row.get("Job Url", "").strip()
        title      = row.get("Job Title", "").strip()
        company    = row.get("Company Name", "").strip()

        parts = []
        if title:      parts.append(f"Saved job: {title}")
        if company:    parts.append(f"Company: {company}")
        if saved_date: parts.append(f"Saved on: {saved_date}")
        if url:        parts.append(f"URL: {url}")

        if not parts:
            continue

        chunks.append(DocumentChunk(
            document="\n".join(parts),
            collection="jobs",
            source="csv",
            type="saved_job",
            entity_id=f"saved_job::{i}",
            entity_name=f"{title} at {company}".strip(" at"),
            company=company or None,
            url=url or None,
            date_from=saved_date or None,
        ))
    print(f"[parse_activity] {len(chunks)} saved job chunks.")
    return chunks


# ─────────────────────────────────────────────
# Saved Job Alerts
# ─────────────────────────────────────────────

def parse_saved_job_alerts() -> list[DocumentChunk]:
    rows = _read_csv(CSV["saved_job_alerts"])
    chunks = []
    for i, row in enumerate(rows):
        params  = row.get("ALERT_PARAMETERS", "").strip()
        query   = row.get("QUERY_CONTEXT", "").strip()
        alert_id = row.get("SAVED_SEARCH_ID", "").strip()

        parts = []
        if query:   parts.append(f"Job alert search: {query}")
        if params:  parts.append(f"Alert filters: {params}")

        if not parts:
            continue

        chunks.append(DocumentChunk(
            document="\n".join(parts),
            collection="jobs",
            source="csv",
            type="saved_job_alert",
            entity_id=f"job_alert::{alert_id or i}",
            entity_name=f"Job Alert: {query[:60]}" if query else f"Job Alert {i}",
        ))
    print(f"[parse_activity] {len(chunks)} job alert chunks.")
    return chunks


# ─────────────────────────────────────────────
# Job Applicant Saved Answers
# ─────────────────────────────────────────────

def parse_saved_answers() -> list[DocumentChunk]:
    rows = _read_csv(CSV["job_saved_answers"])
    chunks = []
    for i, row in enumerate(rows):
        question = row.get("Question", "").strip()
        answer   = row.get("Answer", "").strip()

        if not question or not answer:
            continue

        chunks.append(DocumentChunk(
            document=f"Question: {question}\nAnswer: {answer}",
            collection="my_activity",
            source="csv",
            type="saved_answer",
            entity_id=f"saved_answer::{i}",
            entity_name=f"Saved answer: {question[:60]}",
        ))
    print(f"[parse_activity] {len(chunks)} saved answer chunks.")
    return chunks


# ─────────────────────────────────────────────
# All Likes / Shares
# ─────────────────────────────────────────────

def parse_likes() -> list[DocumentChunk]:
    """
    LinkedIn exports likes/shares as Shares.csv or similar.
    Adjust the CSV key in config if your file has a different name.
    """
    rows = _read_csv(CSV["all_likes"])
    chunks = []
    for i, row in enumerate(rows):
        # Fields vary — try common column names
        date    = (row.get("Date") or row.get("ShareDate") or "").strip()
        content = (row.get("ShareCommentary") or row.get("Content") or "").strip()
        url     = (row.get("SharedUrl") or row.get("Url") or "").strip()
        action  = (row.get("Action") or "Liked").strip()

        if not content and not url:
            continue

        parts = [f"Activity: {action}"]
        if date:    parts.append(f"Date: {date}")
        if content: parts.append(f"Content: {content}")
        if url:     parts.append(f"URL: {url}")

        chunks.append(DocumentChunk(
            document="\n".join(parts),
            collection="my_activity",
            source="csv",
            type="like",
            entity_id=f"like::{i}",
            entity_name=f"Like/Share {i}",
            url=url or None,
            date_from=date or None,
        ))
    print(f"[parse_activity] {len(chunks)} like/share chunks.")
    return chunks


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

def parse_all_activity() -> list[DocumentChunk]:
    chunks = []
    chunks.extend(parse_job_applications())
    chunks.extend(parse_saved_jobs())
    chunks.extend(parse_saved_job_alerts())
    chunks.extend(parse_saved_answers())
    chunks.extend(parse_likes())
    print(f"[parse_activity] Total activity chunks: {len(chunks)}")
    return chunks
