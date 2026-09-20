"""Generic fallback adapter for careers pages on an unrecognized ATS.

Best-effort HTML scraping: pull anchor tags that look like job postings.
No API to rely on, so this is inherently fragile — results are flagged
with department="(unconfirmed)" so the frontend/user can treat them with
appropriately low confidence.
"""

from __future__ import annotations

import hashlib
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .base import REQUEST_TIMEOUT, USER_AGENT, Job

MIN_TITLE_LEN = 4
MAX_TITLE_LEN = 120
MAX_RESULTS = 200

# Common nav/footer link text that isn't a job posting.
SKIP_TEXT = {
    "home", "about", "about us", "contact", "contact us", "privacy",
    "privacy policy", "terms", "terms of service", "login", "log in",
    "sign in", "sign up", "careers", "jobs", "blog", "faq", "help",
}


def fetch_jobs(company_name: str, careers_url: str) -> list[Job]:
    resp = requests.get(
        careers_url,
        timeout=REQUEST_TIMEOUT,
        headers={"User-Agent": USER_AGENT},
    )
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    seen_urls: set[str] = set()
    jobs: list[Job] = []

    for anchor in soup.find_all("a", href=True):
        # separator=" " -- an anchor wrapping multiple child elements (title,
        # department, location as separate nested tags) otherwise gets its
        # text mashed together with no boundary, e.g. "EngineerCore
        # PlatformRemote - USA" instead of "Engineer Core Platform Remote -
        # USA". Collapse the resulting run of whitespace back to single spaces.
        text = " ".join(anchor.get_text(separator=" ", strip=True).split())
        if not (MIN_TITLE_LEN <= len(text) <= MAX_TITLE_LEN):
            continue
        if text.lower() in SKIP_TEXT:
            continue

        href = anchor["href"]
        if href.startswith("#") or href.lower().startswith("mailto:"):
            continue

        full_url = urljoin(careers_url, href)
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)

        jobs.append(
            Job(
                id=hashlib.md5(full_url.encode()).hexdigest(),
                title=text,
                location="",
                url=full_url,
                department="(unconfirmed)",
                company=company_name,
            )
        )

        if len(jobs) >= MAX_RESULTS:
            break

    return jobs
