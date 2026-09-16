"""Ashby adapter — public job board API, no scraping needed."""

from __future__ import annotations

import requests

from .base import REQUEST_TIMEOUT, USER_AGENT, Job, first_path_segment

API_URL = "https://api.ashbyhq.com/posting-api/job-board/{token}"


def fetch_jobs(company_name: str, careers_url: str) -> list[Job]:
    token = first_path_segment(careers_url)
    if not token:
        raise ValueError(f"could not extract an Ashby org token from {careers_url!r}")

    resp = requests.get(
        API_URL.format(token=token),
        params={"includeCompensation": "true"},
        timeout=REQUEST_TIMEOUT,
        headers={"User-Agent": USER_AGENT},
    )
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for entry in data.get("jobs", []):
        jobs.append(
            Job(
                id=str(entry["id"]),
                title=entry.get("title", ""),
                location=entry.get("location", ""),
                url=entry.get("jobUrl", ""),
                department=entry.get("department") or entry.get("team", ""),
                company=company_name,
            )
        )
    return jobs
