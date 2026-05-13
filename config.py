"""
config.py — Central configuration for LinkedIn Career Assistant.
All paths, model IDs, collection names, and chunking params live here.
"""

import os
from pathlib import Path

# ─────────────────────────────────────────────
# Project root (adjust DATA_ROOT to your actual LinkedIn export location)
# ─────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent
DATA_ROOT    = PROJECT_ROOT / "data"          # put your CSVs + MD folders here

# ─────────────────────────────────────────────
# [DEPRECATED] Phase 1 CSV file paths — Not used in Phase 2
# These are preserved for archival reference only.
# Phase 2 uses LinkedIn Portability API snapshots exclusively.
# ─────────────────────────────────────────────
# CSV = {
#     "profile":              DATA_ROOT / "Basic_LinkedInDataExport_04-18-2026" / "Profile.csv",
#     "positions":            DATA_ROOT / "Basic_LinkedInDataExport_04-18-2026" / "Positions.csv",
#     "education":            DATA_ROOT / "Basic_LinkedInDataExport_04-18-2026" / "Education.csv",
#     "skills":               DATA_ROOT / "Basic_LinkedInDataExport_04-18-2026" / "Skills.csv",
#     "certifications":       DATA_ROOT / "Basic_LinkedInDataExport_04-18-2026" / "Certifications.csv",
#     "languages":            DATA_ROOT / "Basic_LinkedInDataExport_04-18-2026" / "Languages.csv",
#     "publications":         DATA_ROOT / "Basic_LinkedInDataExport_04-18-2026" / "Publications.csv",
#     "connections":          DATA_ROOT / "Basic_LinkedInDataExport_04-18-2026" / "Connections.csv",
#     "company_follows":      DATA_ROOT / "Basic_LinkedInDataExport_04-18-2026" / "Company Follows.csv",
#     "messages":             DATA_ROOT / "Basic_LinkedInDataExport_04-18-2026" / "messages.csv",
#     "invitations":          DATA_ROOT / "Basic_LinkedInDataExport_04-18-2026" / "Invitations.csv",
#     "job_applications":     DATA_ROOT / "Basic_LinkedInDataExport_04-18-2026" / "Job Applications.csv",
#     "saved_jobs":           DATA_ROOT / "Basic_LinkedInDataExport_04-18-2026" / "Saved Jobs.csv",
#     "saved_job_alerts":     DATA_ROOT / "Basic_LinkedInDataExport_04-18-2026" / "SavedJobAlerts.csv",
#     "job_saved_answers":    DATA_ROOT / "Basic_LinkedInDataExport_04-18-2026" / "Job Applicant Saved Answers.csv",
# }

# ─────────────────────────────────────────────
# Tavily enrichment folders (MD files)
# Unified Phase 2 location — all enriched MDs live here regardless of phase.
# Phase 1 files were merged into these dirs via enrichment/common.py:sync_legacy_*
# ─────────────────────────────────────────────
TAVILY = {
    "companies_dir":    DATA_ROOT / "enriched" / "companies",
    "connections_dir":  DATA_ROOT / "enriched" / "connections",
}

# ─────────────────────────────────────────────
# ChromaDB
# ─────────────────────────────────────────────
CHROMA_PATH = PROJECT_ROOT / "chroma_db"

COLLECTIONS = {
    "my_profile":       "my_profile",       # own profile, positions, education, skills, certs, langs, pubs
    "my_activity":      "my_activity",      # likes, job applications, saved jobs, saved answers
    "my_network":       "my_network",       # connections CSV + connection Tavily MDs
    "companies":        "companies",        # company follows CSV + company Tavily MDs
    "communications":   "communications",  # full message threads
    "jobs":             "jobs",             # saved jobs + alerts + applications
}

# ─────────────────────────────────────────────
# AWS Bedrock
# ─────────────────────────────────────────────
AWS_REGION = os.getenv("AWS_REGION", "eu-west-1")

BEDROCK_MODELS = {
    # LLM for RAG responses
    "llm": "eu.anthropic.claude-haiku-4-5-20251001-v1:0",

    # Embedding model — pick ONE and keep consistent (changing = re-embed everything)
    # Option A: Amazon Titan (no extra cost beyond Bedrock)
    "embedding": "amazon.titan-embed-text-v2:0",
    "embedding_dim": 1024,

    # Option B: Cohere Embed Multilingual (better for mixed-language data)
    # "embedding": "cohere.embed-multilingual-v3",
    # "embedding_dim": 1024,
}

# ─────────────────────────────────────────────
# Chunking
# ─────────────────────────────────────────────
CHUNK = {
    "profile_max_tokens":   400,    # bio, position descriptions
    "profile_overlap":      0,      # profile sections are self-contained
    "tavily_max_tokens":    500,    # company posts, connection summaries
    "tavily_overlap":       50,
    "tavily_connections_max_tokens": 340,
    "tavily_connections_overlap": 40,
    "tavily_companies_max_tokens": 460,
    "tavily_companies_overlap": 55,
    "messages_max_tokens":  300,    # conversation turns
    "messages_overlap":     100,    # preserve conversation context
    "default_max_tokens":   400,
    "default_overlap":      50,
}

# ─────────────────────────────────────────────
# Ingestion behaviour
# ─────────────────────────────────────────────
INGEST = {
    # Skip re-embedding if content hash unchanged (saves Bedrock costs)
    "skip_unchanged": True,

    # Bedrock embedding rate limit — requests per minute
    "embedding_rpm": 100,

    # Chunk-level quality gates (applied before embedding)
    "min_chunk_chars": 80,
    "min_quality_score": 0.24,
    "max_noise_hits": 2,

    # Your LinkedIn display name (used in system prompt)
    "owner_name": os.getenv("LINKEDIN_OWNER_NAME", "Dimitris"),

    # Set to 1 to print detailed ingest filtering/dedup diagnostics
    "observability": os.getenv("INGEST_OBSERVABILITY", "0") == "1",
}

# ─────────────────────────────────────────────
# LinkedIn Portability API (Phase 2)
# ─────────────────────────────────────────────
PORTABILITY_API = {
    "base_url":     "https://api.linkedin.com/rest",
    "token":        os.getenv("LINKEDIN_PORTABILITY_TOKEN", ""),
    "api_version":  os.getenv("LINKEDIN_API_VERSION", "202312"),
    "snapshot_domains": [
        "PROFILE", "POSITIONS", "EDUCATION", "SKILLS",
        "CERTIFICATIONS", "LANGUAGES", "PUBLICATIONS",
        "CONNECTIONS", "COMPANY_FOLLOWS", "INBOX",
        "JOB_APPLICATIONS", "SAVED_JOBS", "SAVED_JOB_ALERTS",
        "JOB_APPLICANT_SAVED_ANSWERS"
    ],
}
