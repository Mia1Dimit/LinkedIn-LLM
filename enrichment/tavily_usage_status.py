#!/usr/bin/env python3
"""Print Tavily key source and live usage snapshot for diagnostics."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from enrichment.common import get_tavily_usage, resolve_tavily_api_key


def key_source(repo_root: Path) -> str:
    env_key = os.getenv("TAVILY_API_KEY", "").strip()
    if env_key:
        return "env:TAVILY_API_KEY"

    creds_path = repo_root / "data" / "creds" / "tavily_key.json"
    if creds_path.exists():
        try:
            payload = json.loads(creds_path.read_text(encoding="utf-8"))
            if str(payload.get("api_key", "")).strip():
                return "file:data/creds/tavily_key.json"
        except Exception:
            pass

    return "none"


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    key = resolve_tavily_api_key()
    source = key_source(repo_root)

    if not key:
        print("Tavily key source: none")
        print("Tavily usage: unavailable (no API key)")
        return 0

    masked = f"***{key[-4:]}" if len(key) >= 4 else "***"
    usage = get_tavily_usage(key)

    print(f"Tavily key source: {source}")
    print(f"Tavily key fingerprint: {masked}")

    if not usage:
        print("Tavily usage: unavailable (usage API request failed)")
        return 0

    key_usage = usage.get("key", {})
    account_usage = usage.get("account", {})
    print(
        "Tavily usage (key): "
        f"{key_usage.get('usage')} / {key_usage.get('limit')}"
    )
    print(
        "Tavily usage (account plan): "
        f"{account_usage.get('plan_usage')} / {account_usage.get('plan_limit')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
