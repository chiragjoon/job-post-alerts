"""Teamtailor adapter — unauthenticated jobs.json feed.

Not in the original spec, but {slug}.teamtailor.com/jobs.json is a public
JSON Feed (https://jsonfeed.org) that most Teamtailor career sites expose
without auth, confirmed live -- a real API beats routing through the
generic HTML scraper.
"""

from __future__ import annotations

import requests

from .base import REQUEST_TIMEOUT, USER_AGENT, Job, first_path_segment

FEED_URL_TEMPLATE = "https://{slug}.teamtailor.com/jobs.json"


def _slug_from_url(careers_url: str) -> str:
    from urllib.parse import urlparse

    host = urlparse(careers_url).netloc
    if host.endswith(".teamtailor.com"):
        return host.split(".")[0]
    return first_path_segment(careers_url)


def fetch_jobs(company_name: str, careers_url: str) -> list[Job]:
    slug = _slug_from_url(careers_url)
    if not slug:
        raise ValueError(f"could not extract a Teamtailor slug from {careers_url!r}")

    resp = requests.get(
        FEED_URL_TEMPLATE.format(slug=slug),
        timeout=REQUEST_TIMEOUT,
        headers={"User-Agent": USER_AGENT},
    )
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for entry in data.get("items", []):
        job_posting = entry.get("_jobposting") or {}
        locations = job_posting.get("jobLocation") or []
        location = ""
        if locations:
            address = locations[0].get("address") or {}
            location = ", ".join(
                filter(None, [address.get("addressLocality"), address.get("addressCountry")])
            )

        jobs.append(
            Job(
                id=entry.get("id", ""),
                title=entry.get("title", ""),
                location=location,
                url=entry.get("url", ""),
                department="",
                company=company_name,
            )
        )
    return jobs
