"""Lever adapter — public postings API, no scraping needed."""

from __future__ import annotations

import requests

from .base import REQUEST_TIMEOUT, USER_AGENT, Job, first_path_segment

API_URL = "https://api.lever.co/v0/postings/{token}"


def fetch_jobs(company_name: str, careers_url: str) -> list[Job]:
    token = first_path_segment(careers_url)
    if not token:
        raise ValueError(f"could not extract a Lever company token from {careers_url!r}")

    resp = requests.get(
        API_URL.format(token=token),
        params={"mode": "json"},
        timeout=REQUEST_TIMEOUT,
        headers={"User-Agent": USER_AGENT},
    )
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for entry in data:
        categories = entry.get("categories") or {}
        jobs.append(
            Job(
                id=str(entry["id"]),
                title=entry.get("text", ""),
                location=categories.get("location", ""),
                url=entry.get("hostedUrl", ""),
                department=categories.get("team", ""),
                company=company_name,
            )
        )
    return jobs
