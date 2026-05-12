#!/usr/bin/env python3
"""List companies pending enrichment with date filter."""

from pathlib import Path
from enrichment.common import snapshot_rows, slugify_text, file_has_content, parse_date
from enrichment.skip_list import SKIP_COMPANIES
import json
from datetime import datetime

# Load config
config_file = Path('enrichment/enrichment_config.json')
config = json.loads(config_file.read_text())
start_date_str = config.get('companies_enrichment', {}).get('start_date')
start_date = parse_date(start_date_str) if start_date_str else None

# Load companies from snapshot
rows = snapshot_rows('COMPANY_FOLLOWS')
unique_by_org = {}
for row in rows:
    organization = str(row.get('Organization', '')).strip()
    if not organization:
        continue
    existing = unique_by_org.get(organization)
    followed_on = str(row.get('Followed On', '')).strip()
    if existing is None or (parse_date(followed_on) or datetime.min) > (parse_date(existing.get('followed_on', '')) or datetime.min):
        unique_by_org[organization] = {
            'organization': organization,
            'followed_on': followed_on,
        }

companies = sorted(
    unique_by_org.values(),
    key=lambda item: parse_date(item.get('followed_on', '')) or datetime.min,
    reverse=True,
)

# Filter by start_date
if start_date:
    companies = [c for c in companies if (parse_date(c.get('followed_on', '')) or datetime.min) > start_date]

# Remove skip list
companies = [c for c in companies if c['organization'] not in SKIP_COMPANIES]

# Check which ones need enrichment
output_dir = Path('data/enriched/companies')
pending = []
for company in companies:
    slug = slugify_text(company['organization'])
    output_path = output_dir / f"Company_{slug}.md"
    if not file_has_content(output_path):
        pending.append(company)

print(f'\nPending enrichment: {len(pending)} companies (after {start_date_str})\n')
print(f'{"#":<3} {"Company":<45} {"Followed On":<20}')
print('=' * 70)
for i, company in enumerate(pending, 1):
    org = company['organization'][:44]
    date = company['followed_on']
    print(f'{i:<3} {org:<45} {date:<20}')

print(f'\n{"=" * 70}')
