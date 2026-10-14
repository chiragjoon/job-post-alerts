# job-post-alerts

> **Status: archived / no further development.**

A single-user job alert tool. `config.yaml` lists company careers pages
plus title/location filters. A daily GitHub Actions run detects each
site's ATS, fetches postings, filters them, and publishes matches to a
static page — no accounts, no email, no server.

**Live page:** https://chiragjoon.github.io/job-post-alerts/

## Why it was stopped

Plenty of existing job boards already do this well. Keeping up with each
company's ATS quirks (and the manual work of connecting with every job
market) cost more time than the tool saved, so it isn't worth continuing.

## What was built

- Python scraper with per-ATS adapters: Greenhouse, Lever, Ashby,
  SmartRecruiters, Teamtailor, Workable, Workday, plus a generic HTML
  fallback.
- Title/location filters with variant groups, and a diff against
  `data/seen.json` to surface only new postings.
- Daily GitHub Actions run (`.github/workflows/daily-scan.yml`) that
  commits `docs/data/*.json`, rendered by `docs/index.html` on GitHub Pages.
- CLIs to add companies (`src.add_company`, `src.bulk_add_companies`).

Full design: [docs/PLAN.md](docs/PLAN.md).

## If you ever revive it

```
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 -m src.main          # run a scan locally
```

The scheduled workflow can also be triggered from GitHub: Actions →
"Daily job scan" → Run workflow. Archiving the repo disables it.

## Notes

<!-- Add your own notes, learnings, or pointers here. -->
