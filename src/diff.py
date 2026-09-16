"""Tracks which job IDs have already been surfaced, so the daily view only
shows what's new since the last run.
"""

from __future__ import annotations

import json
from pathlib import Path

from .adapters import Job


def _key(job: Job) -> str:
    # Job.id is only guaranteed unique *within* a company (e.g. Workday
    # requisition numbers like "JR1997578" are tenant-scoped, not global),
    # so the dedup/seen key is scoped by company too.
    return f"{job.company}::{job.id}"


def load_seen(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return set(json.loads(path.read_text()))


def compute_new(jobs: list[Job], seen_ids: set[str]) -> list[Job]:
    return [job for job in jobs if _key(job) not in seen_ids]


def write_seen(path: Path, jobs: list[Job], seen_ids: set[str]) -> None:
    all_ids = seen_ids | {_key(job) for job in jobs}
    path.write_text(json.dumps(sorted(all_ids), indent=2))
