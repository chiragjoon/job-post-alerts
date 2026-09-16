"""Title/location filtering against variant groups.

Each group (e.g. ["Frontend Engineer", "Front End Developer"]) represents
one logical thing to match; a job matches a set of groups if it matches
at least one variant in at least one group. Matching is a broad,
case-insensitive substring check by design — start broad, tighten later.
An empty group list means "no filter" (matches everything).
"""

from __future__ import annotations

from .adapters import Job


def _matches_any_group(text: str, groups: list[list[str]]) -> bool:
    if not groups:
        return True
    text_lower = text.lower()
    return any(variant.lower() in text_lower for group in groups for variant in group)


def filter_jobs(jobs: list[Job], titles: list[list[str]], locations: list[list[str]]) -> list[Job]:
    return [
        job
        for job in jobs
        if _matches_any_group(job.title, titles) and _matches_any_group(job.location, locations)
    ]
