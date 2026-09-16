"""Dispatches to the right adapter based on detected ATS."""

from __future__ import annotations

from .base import Job
from . import ashby, generic, greenhouse, lever, smartrecruiters, teamtailor, workable, workday

ADAPTERS = {
    "greenhouse": greenhouse.fetch_jobs,
    "lever": lever.fetch_jobs,
    "ashby": ashby.fetch_jobs,
    "workday": workday.fetch_jobs,
    "smartrecruiters": smartrecruiters.fetch_jobs,
    "workable": workable.fetch_jobs,
    "teamtailor": teamtailor.fetch_jobs,
    "generic": generic.fetch_jobs,
    # oracle_recruiting_cloud, icims, successfactors, taleo, pinpoint have
    # no public API -- they fall through to generic.fetch_jobs below.
}


def fetch_jobs(ats: str, company_name: str, careers_url: str) -> list[Job]:
    fetch = ADAPTERS.get(ats, generic.fetch_jobs)
    return fetch(company_name, careers_url)


__all__ = ["Job", "fetch_jobs", "ADAPTERS"]
