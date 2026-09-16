# job-post-alerts

A single-user job alert tool. `config.yaml` lists company careers pages
plus title/location filters. A daily GitHub Actions run scans them and
publishes matches to a static page — no accounts, no email, no server.

**Live page:** https://chiragjoon.github.io/job-post-alerts/

## Setup (first time)

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Adding a company

There's no form on the site — it's a static page with no backend to save
to. Use the CLI instead:

```
source .venv/bin/activate
python3 -m src.add_company "Company Name" "https://boards.greenhouse.io/company"
```

This detects the ATS and does a live test fetch before writing anything,
so a bad URL is caught immediately instead of failing silently in
tomorrow's scan. It rejects duplicates and won't touch `config.yaml` if
the fetch fails.

New company won't show up on the site until the next scan runs (daily,
or trigger it manually — see below).

## Running a scan manually

```
source .venv/bin/activate
python3 -m src.main
```

Or trigger the scheduled workflow directly from GitHub: Actions →
"Daily job scan" → Run workflow.

## More detail

See [docs/PLAN.md](docs/PLAN.md) for the full design: ATS coverage,
diffing behavior, failure handling, frontend layout.
