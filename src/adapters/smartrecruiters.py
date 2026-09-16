"""SmartRecruiters adapter — public postings API, paginated."""

from __future__ import annotations

import requests

from .base import REQUEST_TIMEOUT, USER_AGENT, Job, first_path_segment

API_URL = "https://api.smartrecruiters.com/v1/companies/{slug}/postings"
PAGE_SIZE = 100


def fetch_jobs(company_name: str, careers_url: str) -> list[Job]:
    slug = first_path_segment(careers_url)
    if not slug:
        raise ValueError(f"could not extract a SmartRecruiters company slug from {careers_url!r}")

    jobs: list[Job] = []
    offset = 0
    while True:
        resp = requests.get(
            API_URL.format(slug=slug),
            params={"offset": offset, "limit": PAGE_SIZE},
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
        )
        resp.raise_for_status()
        data = resp.json()

        content = data.get("content", [])
        for entry in content:
            location = entry.get("location") or {}
            department = entry.get("department") or {}
            company_identifier = (entry.get("company") or {}).get("identifier", slug)
            jobs.append(
                Job(
                    id=str(entry["id"]),
                    title=entry.get("name", ""),
                    location=location.get("fullLocation")
                    or ", ".join(filter(None, [location.get("city"), location.get("region"), location.get("country")])),
                    url=f"https://jobs.smartrecruiters.com/{company_identifier}/{entry['id']}",
                    department=department.get("label", ""),
                    company=company_name,
                )
            )

        offset += PAGE_SIZE
        total = data.get("totalFound", 0)
        if offset >= total or not content:
            break

    return jobs
