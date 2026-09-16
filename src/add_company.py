"""CLI to add a company to config.yaml with an immediate validation fetch.

Usage:
    python3 -m src.add_company "<Company Name>" "<careers_url>"

Runs ATS detection and a live dry-run fetch before writing anything, so a
typo'd URL or unsupported site is caught on the spot instead of silently
showing up as a failure in tomorrow's cron run. See docs/PLAN.md §8.
"""

from __future__ import annotations

import sys
from pathlib import Path

from .adapters import fetch_jobs
from .ats_detect import detect_ats
from .config import load_config
from .filter import filter_jobs

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config.yaml"


def _normalize_url(url: str) -> str:
    return url.strip().rstrip("/").lower()


def _yaml_scalar(value: str) -> str:
    # Always double-quote so a name/URL containing a colon, #, or other
    # YAML-significant character can't break the file.
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _append_to_config(name: str, careers_url: str) -> None:
    lines = CONFIG_PATH.read_text().splitlines(keepends=True)

    start = None
    for i, line in enumerate(lines):
        if line.strip() == "companies:":
            start = i
            break
    if start is None:
        raise SystemExit("config.yaml has no 'companies:' key -- can't append automatically.")

    last_entry_end = start
    i = start + 1
    while i < len(lines) and lines[i].startswith("  "):
        last_entry_end = i
        i += 1

    new_entry = f"  - name: {_yaml_scalar(name)}\n    careers_url: {_yaml_scalar(careers_url)}\n"
    lines.insert(last_entry_end + 1, new_entry)
    CONFIG_PATH.write_text("".join(lines))


def add_company(name: str, careers_url: str) -> None:
    config = load_config(CONFIG_PATH)

    for company in config.companies:
        if company.name.strip().lower() == name.strip().lower():
            raise SystemExit(f"A company named {company.name!r} is already in config.yaml.")
        if _normalize_url(company.careers_url) == _normalize_url(careers_url):
            raise SystemExit(f"{careers_url!r} is already tracked as {company.name!r}.")

    print(f"Detecting ATS for {careers_url} ...")
    ats = detect_ats(careers_url)
    print(f"  -> {ats}")

    print("Fetching jobs to validate the URL ...")
    try:
        jobs = fetch_jobs(ats, name, careers_url)
    except Exception as exc:  # noqa: BLE001 - report and abort, don't add a broken entry
        raise SystemExit(
            f"Could not fetch jobs from {careers_url!r}: {exc}\n"
            "Not added -- fix the URL and try again."
        )

    matched = filter_jobs(jobs, config.titles, config.locations)
    print(f"  -> {len(jobs)} jobs found, {len(matched)} match your current filters")

    _append_to_config(name, careers_url)
    print(f"\nAdded {name!r} to config.yaml. Run `python3 -m src.main` to include it in today's scan.")


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('Usage: python3 -m src.add_company "<Company Name>" "<careers_url>"')
    add_company(sys.argv[1], sys.argv[2])


if __name__ == "__main__":
    main()
