"""Orchestrates one full run: fetch -> filter -> diff -> write output.

Each company is fetched independently; a failure on one company is
recorded in status.json and does not stop the others (see PLAN.md §5).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from . import diff
from .adapters import Job, fetch_jobs
from .ats_detect import detect_ats
from .config import load_config
from .filter import filter_jobs

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config.yaml"
SEEN_PATH = REPO_ROOT / "data" / "seen.json"
DOCS_DATA_DIR = REPO_ROOT / "docs" / "data"
JOBS_PATH = DOCS_DATA_DIR / "jobs.json"
NEW_TODAY_PATH = DOCS_DATA_DIR / "new_today.json"
STATUS_PATH = DOCS_DATA_DIR / "status.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load_previous_status() -> dict:
    if not STATUS_PATH.exists():
        return {}
    try:
        return json.loads(STATUS_PATH.read_text()).get("companies", {})
    except (json.JSONDecodeError, OSError):
        return {}


def run() -> None:
    config = load_config(CONFIG_PATH)
    previous_status = _load_previous_status()

    now = _now_iso()
    company_status: dict[str, dict] = {}
    all_matches: list[Job] = []

    for company in config.companies:
        try:
            ats = detect_ats(company.careers_url)
            jobs = fetch_jobs(ats, company.name, company.careers_url)
            matched = filter_jobs(jobs, config.titles, config.locations)
            all_matches.extend(matched)

            company_status[company.name] = {
                "status": "success",
                "ats": ats,
                "job_count": len(jobs),
                "matched_count": len(matched),
                "last_success": now,
                "error": None,
            }
            print(f"[ok]   {company.name} ({ats}): {len(jobs)} jobs, {len(matched)} matched")
        except Exception as exc:  # noqa: BLE001 - a broken site must not kill the run
            prev = previous_status.get(company.name, {})
            company_status[company.name] = {
                "status": "error",
                "ats": prev.get("ats"),
                "job_count": None,
                "matched_count": None,
                "last_success": prev.get("last_success"),
                "error": str(exc),
            }
            print(f"[fail] {company.name}: {exc}")

    seen_ids = diff.load_seen(SEEN_PATH)
    new_jobs = diff.compute_new(all_matches, seen_ids)

    DOCS_DATA_DIR.mkdir(parents=True, exist_ok=True)
    SEEN_PATH.parent.mkdir(parents=True, exist_ok=True)

    JOBS_PATH.write_text(json.dumps([j.to_dict() for j in all_matches], indent=2))
    NEW_TODAY_PATH.write_text(json.dumps([j.to_dict() for j in new_jobs], indent=2))
    STATUS_PATH.write_text(
        json.dumps({"generated_at": now, "companies": company_status}, indent=2)
    )

    diff.write_seen(SEEN_PATH, all_matches, seen_ids)

    print(f"\n{len(all_matches)} total matches, {len(new_jobs)} new today.")


if __name__ == "__main__":
    run()
