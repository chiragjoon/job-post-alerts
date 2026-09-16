"""Greenhouse adapter — public boards API, no scraping needed."""

from __future__ import annotations

import requests

from .base import REQUEST_TIMEOUT, USER_AGENT, Job, first_path_segment

API_URL = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"


def fetch_jobs(company_name: str, careers_url: str) -> list[Job]:
    token = first_path_segment(careers_url)
    if not token:
        raise ValueError(f"could not extract a Greenhouse board token from {careers_url!r}")

    resp = requests.get(
        API_URL.format(token=token),
        params={"content": "true"},
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
                title=entry["title"],
                location=(entry.get("location") or {}).get("name", ""),
                url=entry.get("absolute_url", ""),
                department=", ".join(d["name"] for d in entry.get("departments", [])),
                company=company_name,
            )
        )
    return jobs
