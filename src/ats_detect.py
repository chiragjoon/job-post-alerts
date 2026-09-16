"""Detects which ATS a careers page URL is using."""

from __future__ import annotations

import re

import requests

DOMAIN_PATTERNS: dict[str, str] = {
    "greenhouse": r"(boards|job-boards)\.greenhouse\.io",
    "lever": r"jobs\.lever\.co",
    "ashby": r"jobs\.ashbyhq\.com",
    "workday": r"myworkdayjobs\.com",
    "smartrecruiters": r"jobs\.smartrecruiters\.com",
    "workable": r"apply\.workable\.com",
    "teamtailor": r"teamtailor\.com",
    # No public API for these -- detection still matters so status.json
    # reports the right ATS name, even though fetching falls back to the
    # generic HTML scraper (see adapters/__init__.py).
    "oracle_recruiting_cloud": r"oraclecloud\.com",
    "icims": r"icims\.com",
    "successfactors": r"(successfactors\.com|sapsf\.com)",
    "taleo": r"taleo\.net",
    "pinpoint": r"pinpointhq\.com",
}

# Signatures to look for when the URL is on the company's own domain and
# the ATS is embedded rather than linked to directly.
HTML_SIGNATURES: dict[str, str] = {
    "greenhouse": "greenhouse.io",
    "lever": "lever.co",
    "ashby": "ashbyhq.com",
    "workday": "myworkdayjobs.com",
    "smartrecruiters": "smartrecruiters.com",
    "workable": "workable.com",
    "teamtailor": "teamtailor.com",
    "oracle_recruiting_cloud": "oraclecloud.com",
    "icims": "icims.com",
    "successfactors": "successfactors.com",
    "taleo": "taleo.net",
    "pinpoint": "pinpointhq.com",
}

REQUEST_TIMEOUT = 10
USER_AGENT = "job-post-alerts/1.0 (+https://github.com/)"


def detect_ats(url: str) -> str:
    for ats, pattern in DOMAIN_PATTERNS.items():
        if re.search(pattern, url):
            return ats

    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
        html = resp.text.lower()
        for ats, signature in HTML_SIGNATURES.items():
            if signature in html:
                return ats
    except requests.RequestException:
        pass

    return "generic"
