#!/usr/bin/env python3
"""
Compatibility wrapper for Windows PowerShell sync orchestration.

Primary runner:
    ./sync_all_data.ps1

This Python entry point is intentionally kept so existing habits or schedulers
that call `python sync_all_data.py` continue to work.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def build_ps_command(args: argparse.Namespace, script_path: Path) -> list[str]:
    cmd = [
        "pwsh",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script_path),
    ]

    if args.skip_fetch:
        cmd.append("-SkipFetch")
    if args.skip_enrich:
        cmd.append("-SkipEnrich")
    if args.skip_ingest:
        cmd.append("-SkipIngest")
    if args.stats_only:
        cmd.append("-StatsOnly")
    if args.continue_on_error:
        cmd.append("-ContinueOnError")
    if args.force_fetch:
        cmd.append("-ForceFetch")
    if args.force_ingest:
        cmd.append("-ForceIngest")

    cmd.extend(["-SnapshotFreshHours", str(args.snapshot_fresh_hours)])
    if args.tavily_api_key:
        cmd.extend(["-TavilyApiKey", args.tavily_api_key])
    if args.tavily_project_id:
        cmd.extend(["-TavilyProjectId", args.tavily_project_id])

    cmd.extend(["-LogDir", args.log_dir])
    return cmd


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run modular LinkedIn sync pipeline via PowerShell with timestamped logs."
    )
    parser.add_argument("--skip-fetch", action="store_true", help="Skip snapshot fetch stage.")
    parser.add_argument("--skip-enrich", action="store_true", help="Skip enrichment stage.")
    parser.add_argument("--skip-ingest", action="store_true", help="Skip ingest stage.")
    parser.add_argument("--stats-only", action="store_true", help="Only run stats commands.")
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue running next steps after a failed step.",
    )
    parser.add_argument(
        "--force-fetch",
        action="store_true",
        help="Force fetch even if cached snapshots are fresh.",
    )
    parser.add_argument(
        "--force-ingest",
        action="store_true",
        help="Force ingest even if fetch/enrich were skipped.",
    )
    parser.add_argument(
        "--snapshot-fresh-hours",
        type=int,
        default=24,
        help="Skip fetch when latest snapshot is newer than this threshold.",
    )
    parser.add_argument(
        "--tavily-api-key",
        default="",
        help="Override Tavily API key for this run only.",
    )
    parser.add_argument(
        "--tavily-project-id",
        default="",
        help="Optional Tavily project ID for usage scoping.",
    )
    parser.add_argument(
        "--log-dir",
        default="logs/sync",
        help="Directory where timestamped log files are written.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent
    script_path = repo_root / "sync_all_data.ps1"

    if not script_path.exists():
        print("ERROR: sync_all_data.ps1 not found next to sync_all_data.py")
        return 1

    if sys.platform != "win32":
        print("ERROR: This wrapper targets Windows PowerShell (pwsh).")
        print(f"Run script directly: {script_path}")
        return 1

    cmd = build_ps_command(args, script_path)
    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=repo_root)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
