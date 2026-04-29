# LinkedIn Career Assistant

Personal RAG-powered career intelligence built on your LinkedIn data.
Runs fully locally on your personal machine. Uses AWS Bedrock for embeddings and LLM.

## Stack
- **Vector DB**: ChromaDB (local, no server needed)
- **Embeddings**: AWS Bedrock — Amazon Titan Embed v2 or Cohere Embed Multilingual
- **LLM**: AWS Bedrock — Claude 3 Sonnet
- **Data**: LinkedIn ZIP export + Tavily enrichment MDs

---

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure AWS credentials
```bash
aws configure
# Enter your AWS Access Key, Secret, and region (e.g. eu-west-1)
```

Make sure your IAM user has `bedrock:InvokeModel` permission for:
- `amazon.titan-embed-text-v2:0`
- `anthropic.claude-3-sonnet-20240229-v1:0`

### 3. Set your name
```bash
export LINKEDIN_OWNER_NAME="Dimitris"
```

### 4. Organise your data
```
data/
├── Basic_LinkedInDataExport_04-18-2026/
│   ├── Profile.csv
│   ├── Positions.csv
│   ├── Connections.csv
│   ├── Company Follows.csv      # 3rd column "LinkedIn URL" manually added
│   ├── Education.csv
│   ├── Skills.csv
│   ├── Certifications.csv
│   ├── Languages.csv
│   ├── Publications.csv
│   ├── messages.csv
│   ├── Invitations.csv
│   ├── Job Applications.csv
│   ├── Saved Jobs.csv
│   ├── SavedJobAlerts.csv
│   └── Job Applicant Saved Answers.csv
└── tavily/
    ├── companies/               # Tavily extract MD files (1 per company)
    └── connections/             # Tavily search MD files (1 per connection)
```

### 5. Update config.py if needed
- Check `CSV` paths match your actual filenames exactly
- Set `AWS_REGION` to your preferred region
- Choose embedding model (Titan vs Cohere) — **pick one and stick with it**

---

## Usage

### Phase 1: Dry run (no Bedrock calls, just parsing)
```bash
python ingest.py --dry-run
```
Use this first to verify all CSVs parse correctly before spending Bedrock credits.

### Ingest everything
```bash
python ingest.py
```

### Ingest one section at a time
```bash
python ingest.py --only profile
python ingest.py --only network
python ingest.py --only companies
python ingest.py --only activity
python ingest.py --only messages
```

### Check what's in ChromaDB
```bash
python ingest.py --stats
```

### Ask a question
```bash
python query/ask.py "Who do I know at AWS?"
python query/ask.py "What roles have I applied for in the last year?"
python query/ask.py "Which companies in my network are in fintech?"
python query/ask.py "Summarise my career trajectory"
python query/ask.py "What skills do I have that match a senior PM role?"
```

### Interactive mode
```bash
python query/ask.py --interactive
```

### Debug: see what context was retrieved
```bash
python query/ask.py "Who do I know at Google?" --verbose
```

---

## Project Structure

```
linkedin_assistant/
├── config.py                   # All paths, model IDs, collection names
├── ingest.py                   # Main ingestion orchestrator
├── requirements.txt
├── data/
│   ├── csv/                    # LinkedIn ZIP CSVs
│   └── tavily/
│       ├── companies/          # Tavily extract MDs
│       └── connections/        # Tavily search MDs
├── chroma_db/                  # ChromaDB persistent storage (auto-created)
├── parsers/
│   ├── parse_profile.py        # Profile, positions, education, skills, certs, langs, pubs
│   ├── parse_network.py        # Connections CSV + Tavily connection MDs
│   ├── parse_companies.py      # Company follows CSV + Tavily company MDs
│   ├── parse_activity.py       # Job applications, saved jobs, likes, saved answers
│   └── parse_messages.py       # Full message threads
├── db/
│   └── vector_store.py         # ChromaDB + Bedrock embedder
├── query/
│   └── ask.py                  # RAG retriever + Bedrock Claude
└── utils/
    ├── schema.py               # Unified DocumentChunk schema
    └── chunker.py              # Text splitter
```

---

## Phase 2 (coming next)

- `ingestion/snapshot_api.py` — pull all domains from LinkedIn Portability Snapshot API
- `ingestion/changelog_api.py` — weekly poll of Portability Changelog API
- `ingestion/cron.py` — scheduler (weekly Tavily + Changelog, monthly Snapshot)
- Replace CSVs as source of truth with API JSON — same parsers, new adapters
