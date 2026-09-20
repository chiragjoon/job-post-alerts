"""Teamtailor adapter — unauthenticated jobs.json feed.

Not in the original spec, but /jobs.json is a public JSON Feed
(https://jsonfeed.org) that most Teamtailor career sites expose without
auth, confirmed live -- a real API beats routing through the generic HTML
scraper. It's served on whatever host the company's board lives on --
{slug}.teamtailor.com for most, but also on a company's own custom domain
(e.g. careers.arbolus.com/jobs.json) -- so this hits the careers_url's own
host rather than assuming the teamtailor.com subdomain shape.
"""

from __future__ import annotations

from urllib.parse import urlparse

import requests

from .base import REQUEST_TIMEOUT, USER_AGENT, Job

FEED_PATH = "/jobs.json"


def fetch_jobs(company_name: str, careers_url: str) -> list[Job]:
    host = urlparse(careers_url).netloc
    if not host:
        raise ValueError(f"could not extract a host from {careers_url!r}")

    resp = requests.get(
        f"https://{host}{FEED_PATH}",
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
