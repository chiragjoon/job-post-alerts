"""Workable adapter — POST to the v3 jobs API.

Field names below are parsed defensively (.get() with fallbacks): the
endpoint's wrapper shape ({"total": int, "results": [...]}) was confirmed
live, but a nonzero-result account wasn't found during development to
lock down every inner field name. If a field turns out wrong, this fails
loudly per-company (see main.py) rather than silently -- fix the field
name here once you see the real error.
"""

from __future__ import annotations

import requests

from .base import REQUEST_TIMEOUT, USER_AGENT, Job, first_path_segment

API_URL = "https://apply.workable.com/api/v3/accounts/{slug}/jobs"
PAGE_SIZE = 50


def fetch_jobs(company_name: str, careers_url: str) -> list[Job]:
    slug = first_path_segment(careers_url)
    if not slug:
        raise ValueError(f"could not extract a Workable account slug from {careers_url!r}")

    jobs: list[Job] = []
    offset = 0
    while True:
        resp = requests.post(
            API_URL.format(slug=slug),
            json={"limit": PAGE_SIZE, "offset": offset},
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT, "Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()

        results = data.get("results", [])
        for entry in results:
            shortcode = entry.get("shortcode", "")
            locations = entry.get("locations") or []
            location = ""
            if locations:
                loc = locations[0].get("location") or locations[0]
                location = ", ".join(
                    filter(None, [loc.get("city"), loc.get("region"), loc.get("country")])
                )
            elif entry.get("telecommuting"):
                location = "Remote"

            jobs.append(
                Job(
                    id=entry.get("id") or shortcode,
                    title=entry.get("title", ""),
                    location=location,
                    url=entry.get("url") or f"https://apply.workable.com/{slug}/j/{shortcode}/",
                    department=entry.get("department", ""),
                    company=company_name,
                )
            )

        offset += PAGE_SIZE
        total = data.get("total", 0)
        if offset >= total or not results:
            break

    return jobs
