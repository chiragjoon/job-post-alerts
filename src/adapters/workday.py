"""Workday adapter — POST to the CXS API, paginated.

Career URLs look like:
  https://{tenant}.{wdN}.myworkdayjobs.com/{locale}/{site}
e.g. https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite

The CXS endpoint is:
  https://{tenant}.{wdN}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs
"""

from __future__ import annotations

from urllib.parse import urlparse

import requests

from .base import REQUEST_TIMEOUT, USER_AGENT, Job

PAGE_SIZE = 20  # Workday's CXS API rejects limit > 20 with a 400
MAX_OFFSET = 5000  # safety cap so a huge/misbehaving board can't loop forever


def _parse_workday_url(careers_url: str) -> tuple[str, str, str, str]:
    parsed = urlparse(careers_url)
    host_parts = parsed.netloc.split(".")
    if len(host_parts) < 2:
        raise ValueError(f"not a myworkdayjobs.com URL: {careers_url!r}")
    tenant = host_parts[0]

    path_segments = [seg for seg in parsed.path.split("/") if seg]
    if len(path_segments) >= 2:
        locale, site = path_segments[0], path_segments[1]
    elif len(path_segments) == 1:
        locale, site = "en-US", path_segments[0]
    else:
        raise ValueError(f"could not find a Workday site name in {careers_url!r}")

    return tenant, parsed.netloc, locale, site


def fetch_jobs(company_name: str, careers_url: str) -> list[Job]:
    tenant, host, locale, site = _parse_workday_url(careers_url)
    api_url = f"https://{host}/wday/cxs/{tenant}/{site}/jobs"

    # Workday's `total` field has been observed flipping between 0 and the
    # real count across pages of the *same* query, and pages past the real
    # end repeat earlier results instead of coming back empty. So instead
    # of trusting `total` to know when to stop, we dedupe by job ID within
    # this fetch and stop once a full page adds nothing new.
    jobs: list[Job] = []
    seen_ids: set[str] = set()
    offset = 0
    while True:
        resp = requests.post(
            api_url,
            json={"appliedFacets": {}, "limit": PAGE_SIZE, "offset": offset, "searchText": ""},
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT, "Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()

        postings = data.get("jobPostings", [])
        new_count = 0
        for entry in postings:
            external_path = entry.get("externalPath", "")
            bullet_fields = entry.get("bulletFields") or []
            job_id = bullet_fields[0] if bullet_fields else external_path

            if job_id in seen_ids:
                continue
            seen_ids.add(job_id)
            new_count += 1

            jobs.append(
                Job(
                    id=job_id,
                    title=entry.get("title", ""),
                    location=entry.get("locationsText", ""),
                    url=f"https://{host}/{locale}/{site}{external_path}",
                    department="",
                    company=company_name,
                )
            )

        offset += PAGE_SIZE
        if len(postings) < PAGE_SIZE or new_count == 0 or offset >= MAX_OFFSET:
            break

    return jobs
