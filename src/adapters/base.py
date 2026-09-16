"""Shared Job shape and URL helpers used by every adapter."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

REQUEST_TIMEOUT = 15
USER_AGENT = "job-post-alerts/1.0 (+https://github.com/)"


@dataclass
class Job:
    id: str
    title: str
    location: str
    url: str
    department: str
    company: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "location": self.location,
            "url": self.url,
            "department": self.department,
            "company": self.company,
        }


def first_path_segment(url: str) -> str:
    path = urlparse(url).path.strip("/")
    return path.split("/")[0] if path else ""
