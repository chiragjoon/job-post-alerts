"""Bulk-add companies listed in a Markdown table.

Usage:
    python3 -m src.bulk_add_companies [path]

Defaults to companies_to_add.md at the repo root. Each row gets the same
validation as src.add_company (ATS detection + live dry-run fetch). Rows
that succeed are removed from the file; rows that fail are left in place
so you can fix and rerun without retyping the whole list. See
docs/PLAN.md §9.
"""

from __future__ import annotations

import sys
from pathlib import Path

from .add_company import CompanyAddError, add_company

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATH = REPO_ROOT / "companies_to_add.md"

HEADER_PREFIX = "| Name"


def _parse_rows(lines: list[str]) -> list[tuple[int, str, str]]:
    rows = []
    in_table = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not in_table:
            if stripped.startswith(HEADER_PREFIX):
                in_table = True
            continue
        if not stripped.startswith("|"):
            break

        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if all(set(c) <= {"-"} for c in cells):  # separator row: | --- | --- |
            continue
        if len(cells) < 2 or not cells[0] or not cells[1]:
            continue
        rows.append((i, cells[0], cells[1]))
    return rows


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PATH
    if not path.exists():
        raise SystemExit(f"{path} does not exist.")

    lines = path.read_text().splitlines(keepends=True)
    rows = _parse_rows(lines)

    if not rows:
        raise SystemExit(f"No rows found in {path}. Add some under the '{HEADER_PREFIX}' table.")

    succeeded_line_indices = set()
    added: list[tuple[str, str, int, int]] = []
    skipped: list[tuple[str, str]] = []

    for line_index, name, url in rows:
        print(f"\n=== {name} ===")
        try:
            ats, job_count, matched_count = add_company(name, url)
            succeeded_line_indices.add(line_index)
            added.append((name, ats, job_count, matched_count))
        except CompanyAddError as exc:
            print(f"  SKIPPED: {exc}")
            skipped.append((name, str(exc)))

    remaining_lines = [line for i, line in enumerate(lines) if i not in succeeded_line_indices]
    path.write_text("".join(remaining_lines))

    print("\n--- Summary ---")
    if added:
        print(f"Added {len(added)}:")
        for name, ats, job_count, matched_count in added:
            print(f"  - {name} ({ats}): {job_count} jobs, {matched_count} matched")
    if skipped:
        print(f"Skipped {len(skipped)} (left in {path.name} for you to fix):")
        for name, reason in skipped:
            print(f"  - {name}: {reason}")
    if added:
        print("\nRun `python3 -m src.main` to include new companies in today's scan.")


if __name__ == "__main__":
    main()
