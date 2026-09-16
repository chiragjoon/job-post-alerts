"""Loads and validates config.yaml."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Company:
    name: str
    careers_url: str


@dataclass
class Config:
    companies: list[Company]
    titles: list[list[str]] = field(default_factory=list)
    locations: list[list[str]] = field(default_factory=list)


def load_config(path: Path) -> Config:
    raw = yaml.safe_load(path.read_text()) or {}

    companies_raw = raw.get("companies") or []
    if not companies_raw:
        raise ValueError("config.yaml must define at least one company under 'companies'")

    companies = []
    for entry in companies_raw:
        if "name" not in entry or "careers_url" not in entry:
            raise ValueError(f"company entry missing 'name' or 'careers_url': {entry}")
        companies.append(Company(name=entry["name"], careers_url=entry["careers_url"]))

    filters = raw.get("filters") or {}
    titles = filters.get("titles") or []
    locations = filters.get("locations") or []

    return Config(companies=companies, titles=titles, locations=locations)
