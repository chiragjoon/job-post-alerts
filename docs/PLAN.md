# Plan

## Architecture

No server, no database. A config file drives a Python scraper that GitHub
Actions runs daily; output is JSON committed to the repo; a static page
(GitHub Pages) renders it.

```
job-post-alerts/
  config.yaml                 # careers URLs + title/location filters (with variants)
  src/
    main.py                   # orchestrates the whole run
    ats_detect.py             # figure out which ATS a URL uses
    adapters/
      greenhouse.py
      lever.py
      ashby.py
      generic.py              # fallback HTML scraping
    filter.py                 # title/location matching w/ variants
    diff.py                   # compare against seen.json, find new jobs
  data/
    seen.json                 # all job IDs ever surfaced (internal, not served)
  docs/
    index.html                # reads ./data/*.json
    data/
      jobs.json              # current matches (full list)
      new_today.json         # subset: jobs not in seen.json
      status.json            # per-company last-run outcome
    PLAN.md                   # this file
  .github/workflows/
    daily-scan.yml
  requirements.txt
```

## 1. Config

`config.yaml`: a list of companies (`name`, `careers_url`), plus filters.
Filters support **variant groups** instead of single strings, e.g.:

```yaml
titles:
  - ["Frontend Engineer", "Front End Developer", "FE Engineer"]
locations:
  - ["Bangalore", "Bengaluru"]
```

Each group is one logical thing to match; matching is case-insensitive
substring against every variant in the group. Start broad (any variant
hits) — tightening (word-boundary matching, excluding "Senior", etc.) is a
later refinement once we see false-positive rates in practice, not
something to over-engineer in v1.

## 2. ATS detection & adapters

Cheapest check first: match the URL against known domain patterns. If the
URL is a company's own domain, fetch the page and sniff for ATS
signatures (script tags, API calls, known div/class names). Unmatched
sites fall back to "generic."

Adapters, one per ATS, normalize results into a common
`{id, title, location, url, department, company}` shape. Coverage, by
where each ATS tends to show up:

| Segment | ATS | Endpoint | Adapter |
|---|---|---|---|
| Tech / fintech scaleups | Greenhouse | `GET boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true` | dedicated |
| | Ashby | `GET api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true` | dedicated |
| | Lever | `GET api.lever.co/v0/postings/{slug}?mode=json` | dedicated |
| Large finance (banks, insurers) | Workday | `POST {tenant}.wd{N}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs` (paginated, `limit` capped at 20 by the API) | dedicated |
| | Oracle Recruiting Cloud | no public API | generic fallback |
| | iCIMS | no public API | generic fallback |
| Industrial / manufacturing / energy | Workday | as above | dedicated |
| | SAP SuccessFactors | no public API | generic fallback |
| | iCIMS / Taleo | no public API | generic fallback |
| Midsize non-tech | SmartRecruiters | `GET api.smartrecruiters.com/v1/companies/{slug}/postings` (paginated) | dedicated |
| | Workable | `POST apply.workable.com/api/v3/accounts/{slug}/jobs` (paginated) | dedicated, field names not confirmed against a live nonzero example — fails loudly per-company if wrong, see §5 |
| | Pinpoint | no public API found | generic fallback |
| | Teamtailor | `GET {slug}.teamtailor.com/jobs.json` — unauthenticated JSON Feed, found during implementation (not in original spec) | dedicated |

Generic fallback — best-effort HTML parsing (BeautifulSoup) for anything
unrecognized or with no public API; flagged as lower-confidence
(`department: "(unconfirmed)"`). Detection still runs for the no-API
systems above even though fetching falls through to generic — this keeps
`status.json` reporting the correct ATS name instead of "generic" for
those.

Every adapter must emit a **stable job ID** per posting (native ID from
Greenhouse/Lever/Ashby APIs; for generic fallback, a hash of the job URL).
This ID is what diffing keys off of — without it, diffing can't tell
"still open" from "reposted."

## 3. Filtering

Matches against variant groups as above. Runs after fetch, before diffing.

## 4. Diffing

`diff.py` compares this run's matched jobs against `data/seen.json`, keyed
by `"{company}::{job.id}"` rather than the raw ID alone — Workday
requisition numbers (e.g. `JR1997578`) are only unique within a tenant,
not globally, so an unscoped key could collide across two different
tracked companies.

- Jobs not already in `seen.json` → written to `docs/data/new_today.json`,
  and added to `seen.json`.
- `docs/data/jobs.json` keeps the full current match list (so the page can
  still show "everything open right now," not just deltas) —
  `new_today.json` is what you'd actually want to glance at daily.
- `data/seen.json` only grows (job IDs, not full job data) — it's an
  internal dedup log, not something the page reads.

## 5. Failure handling

Each company's fetch+filter runs in its own try/except in `main.py`; a
failure doesn't abort the run for other companies. Every company's outcome
(`success` / `error` + message + timestamp) is written to
`docs/data/status.json` regardless of pass/fail. The frontend shows this
per-company (and a global "last successful run" timestamp) so a broken
Greenhouse endpoint returning zero jobs is visibly distinct from "no new
postings today."

## 6. GitHub Actions

`daily-scan.yml`: scheduled cron, checkout, run `main.py`, commit
`data/seen.json` and `docs/data/*.json`. Commit happens even on partial
failure, since `status.json` needs to reflect the failure. GitHub Pages
is configured to serve from the `/docs` folder, so `docs/index.html` and
everything under `docs/data/` are reachable at the published URL — files
outside `docs/` (like `data/seen.json`) are not published, which is why
seen.json lives outside it.

## 7. Frontend

Static page reads `data/new_today.json` (primary view), `data/jobs.json`
(full list, secondary/collapsible), and `data/status.json` (health strip
at the top — red/green per company, last successful run time), all via
relative paths from `docs/index.html`.

### Page setup

Single column, stacks top to bottom, mobile-friendly (this gets checked
on a phone). No build step, no framework — plain HTML + `fetch()` for the
three JSON files + minimal CSS.

```
┌─────────────────────────────────────────────┐
│  Job Alerts                                  │
│  Last full run: Sep 16, 2026 — 6:03 AM       │
├─────────────────────────────────────────────┤
│  Status strip (compact row of pills)         │
│  🟢 Stripe   🟢 Notion   🔴 Figma   🟢 Ashby  │
│  (click a 🔴 to see the error + timestamp)   │
├─────────────────────────────────────────────┤
│  NEW TODAY (3)                    ← default  │
│  ─────────────────────────────    open       │
│  • Frontend Engineer — Stripe — Remote        │
│  • Front End Developer — Notion — Bangalore   │
│  • FE Engineer — Ashby — Remote               │
│  (each row links out to the actual posting)   │
│                                                │
│  or, if empty:                                │
│  "No new postings today."                     │
├─────────────────────────────────────────────┤
│  ▸ All open matches (27)          ← collapsed │
│    by default, click to expand                │
│    - same row format, grouped by company      │
│    - optional client-side text filter box     │
│      (title/location substring, no backend    │
│      needed since it's all in jobs.json)      │
└─────────────────────────────────────────────┘
```

Key choices:

- **Status strip is always visible, never buried** — this is what turns a
  "quiet day" into a visibly "broken scraper" (see §5, Failure handling).
- **"New Today" is the default view** — that's what's actually worth
  checking daily; a growing list of already-seen open roles is noise.
- **"All matches" is collapsed but present** — useful for the full
  picture (e.g. confirming a company's listing actually updated this
  week) without cluttering the daily glance.
- **Each job row links directly to the posting** on the company's ATS —
  the page is a jumping-off point, not a destination.

## Build order

1. Config loader + schema (with variant groups)
2. ATS detection (domain-pattern matching first)
3. Greenhouse + Lever + Ashby adapters, each emitting stable job IDs
4. Filtering logic (variant matching)
5. Diffing (`seen.json` / `new_today.json`)
6. Per-company try/except + `status.json`
7. Static frontend (new-today view + full list + status strip)
8. GitHub Actions workflow
9. Generic fallback adapter for unrecognized ATSs

## Known risks

Oracle Recruiting Cloud, iCIMS, SAP SuccessFactors, Taleo, and Pinpoint
have no public API, so they're detected correctly but fetched via the
generic HTML scraper — inherently fragile against arbitrary company
sites, and likely to miss postings on JS-rendered career pages entirely.
The Workable adapter's field names are best-effort (see §2) and may need
a fix once run against a company with live postings.

## Open question

Should location/title aliasing ship with a built-in default list (e.g.
common Indian city name variants), or stay purely user-supplied groups?
