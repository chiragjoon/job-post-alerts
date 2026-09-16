"""Workday adapter — POST to the CXS API, paginated.

Career URLs look like:
  https://{tenant}.{wdN}.myworkdayjobs.com/{locale}/{site}
e.g. https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite

The CXS endpoint is:
  https://{tenant}.{wdN}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs
"""

from __future__ import annotations

import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse

import requests

from .base import REQUEST_TIMEOUT, USER_AGENT, Job

PAGE_SIZE = 20  # Workday's CXS API rejects limit > 20 with a 400
MAX_OFFSET = 5000  # safety cap so a huge/misbehaving board can't loop forever
RESOLVE_WORKERS = 8  # concurrent detail-fetch requests; keep modest, single ATS backend

# The list endpoint collapses a multi-location posting's locationsText
# down to a bare count ("2 Locations") instead of naming them -- see
# resolve_ambiguous_locations() and docs/PLAN.md §10.
LOCATION_COUNT_PATTERN = re.compile(r"^\d+ Locations?$")


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


def _job_detail_url(job_url: str) -> str:
    parsed = urlparse(job_url)
    segments = [seg for seg in parsed.path.split("/") if seg]
    if len(segments) < 3:
        raise ValueError(f"not a Workday job URL: {job_url!r}")
    tenant = parsed.netloc.split(".")[0]
    site = segments[1]
    external_path = "/" + "/".join(segments[2:])
    return f"https://{parsed.netloc}/wday/cxs/{tenant}/{site}{external_path}"


def _cache_key(job: Job) -> str:
    # Company-scoped for the same reason as diff.py's seen-key: Workday
    # requisition numbers aren't globally unique across tenants.
    return f"{job.company}::{job.id}"


def load_location_cache(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def save_location_cache(path: Path, cache: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, indent=2, sort_keys=True))


def _fetch_detail_location(job: Job) -> str | None:
    resp = requests.get(
        _job_detail_url(job.url),
        timeout=REQUEST_TIMEOUT,
        headers={"User-Agent": USER_AGENT},
    )
    resp.raise_for_status()
    info = resp.json().get("jobPostingInfo", {})
    locations = ([info["location"]] if info.get("location") else []) + list(
        info.get("additionalLocations") or []
    )
    return "; ".join(locations) if locations else None


def resolve_ambiguous_locations(jobs: list[Job], cache: dict[str, str]) -> list[Job]:
    """Mutates jobs in place: any Workday job whose location is a bare
    count ("2 Locations") gets the real place names via the per-job
    detail endpoint -- or from `cache` if already resolved on a previous
    run, so the steady-state daily cost is just newly-seen ambiguous
    postings, not all of them every time. `cache` is mutated in place
    with new results; only a successful resolution is cached (a timeout
    isn't, so it's retried next run). See docs/PLAN.md §10.

    Cache hits are resolved inline (free); cache misses are the only
    thing dispatched to the thread pool, so a fully-warm cache does no
    network work and returns immediately.
    """
    to_resolve: list[Job] = []
    for job in jobs:
        if "myworkdayjobs.com" not in job.url:
            continue
        if not LOCATION_COUNT_PATTERN.match(job.location.strip()):
            continue

        key = _cache_key(job)
        if key in cache:
            job.location = cache[key]
        else:
            to_resolve.append(job)

    if not to_resolve:
        return jobs

    cache_lock = threading.Lock()

    def resolve_one(job: Job) -> None:
        try:
            location = _fetch_detail_location(job)
            if location:
                job.location = location
                with cache_lock:
                    cache[_cache_key(job)] = location
        except Exception as exc:  # noqa: BLE001 - leave the ambiguous text, don't break the run
            print(f"  [warn] could not resolve location for {job.title!r} ({job.company}): {exc}")

    with ThreadPoolExecutor(max_workers=RESOLVE_WORKERS) as executor:
        list(executor.map(resolve_one, to_resolve))

    return jobs
