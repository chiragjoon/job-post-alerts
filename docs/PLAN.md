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
    location_cache.json       # resolved Workday locations, keyed by company::id (§10)
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

## 8. Adding companies (CLI)

A small CLI, `python3 -m src.add_company "<name>" "<careers_url>"`, as a
faster/safer alternative to hand-editing `config.yaml`:

- Runs ATS detection + a live dry-run fetch against the URL immediately,
  so a typo'd token or unsupported site is caught on the spot instead of
  silently showing up as a failure in tomorrow's cron run.
- Refuses to add a duplicate (same name or same URL already in the file).
- Appends the entry into the `companies:` list via targeted text
  insertion, not a full YAML rewrite — keeps the existing comments and
  formatting in `config.yaml` intact (a round-trip YAML dump would drop
  them).
- Prints a summary on success: ATS detected, total jobs found, how many
  match the current filters.

Out of scope for this pass: removing/editing existing companies, editing
filters, any web UI — this is purely "add one company, safely," matching
the file-based, no-server architecture (§ Architecture).

## 9. Bulk-adding companies (Markdown list)

For adding several companies at once instead of one CLI call per
company: `companies_to_add.md` at the repo root holds a simple Markdown
table (`| Name | Careers URL |`) the user fills in by hand, plus
`python3 -m src.bulk_add_companies` to process it.

- Reuses the same per-company logic as `src.add_company` (ATS detection,
  live dry-run fetch, duplicate check) for every row — no separate
  validation path to keep in sync.
- Processes rows independently: one bad URL doesn't block the rest of
  the batch, same "loud failures, isolated per item" principle as the
  daily scan itself (§5).
- Successfully added rows are removed from `companies_to_add.md`
  automatically; rows that fail (bad URL, duplicate) are left in place
  untouched, with the reason printed to the console — so a rerun after
  fixing a URL doesn't require retyping the whole list.
- `src.add_company`'s single-company function is refactored to raise a
  plain exception on failure instead of calling `sys.exit`, so the bulk
  runner can catch per-row failures and keep going; the single-company
  CLI entry point catches that exception and converts it to `sys.exit`
  itself, so its behavior from the outside is unchanged.

Out of scope: editing/removing existing companies in bulk, any format
other than the one Markdown table (e.g. CSV upload), running as part of
the scheduled Action (this stays a manually-run local command, same as
`add_company`).

## 10. Fixing ambiguous Workday locations ("N Locations")

**Problem, confirmed against live data:** Workday's job-list endpoint
(`/wday/cxs/.../jobs`, used by `workday.py`) returns `locationsText` as a
literal count summary — `"2 Locations"`, `"5 Locations"` — for any
posting with more than one location, instead of naming them. A
single-location posting shows the real place (`"Israel, Yokneam"`); a
multi-location one doesn't. Checked against the current dataset: 455 of
1279 matched jobs are affected, all from NVIDIA (the only Workday
company configured) — 0 from Greenhouse/Ashby/Lever/SmartRecruiters/
Teamtailor, so this is Workday-specific, not a general filtering bug.

This silently breaks location filtering: a job open in "Bangalore" among
3 locations shows up as `"3 Locations"`, which a substring match against
`["Bangalore"]` will never hit — the job just vanishes instead of
matching.

**Fix:** Workday also exposes a per-job detail endpoint —
`GET /wday/cxs/{tenant}/{site}/job/{externalPath}` — confirmed live to
return `jobPostingInfo.location` (primary) and
`jobPostingInfo.additionalLocations` (array of the rest). When a job's
`locationsText` matches `^\d+ Locations?$`, fetch this endpoint and join
the real location strings instead.

**Where this runs in the pipeline matters:** it has to happen *after*
title filtering (no point resolving locations for jobs that don't match
the title filter anyway) but *before* location filtering (that's the
thing being fixed). This means `filter.py`'s single combined
`filter_jobs()` needs to split into separate title/location matching
steps, with a resolution pass for ambiguous Workday locations in between,
orchestrated from `main.py`.

**Cost, measured against the current config:** bounded to jobs that
already passed the title filter *and* have the ambiguous pattern —
currently ~455 extra requests, all against NVIDIA. Measured live: this
added ~15-20 minutes to the daily scan (on top of the ~3 min the rest of
the pipeline, including NVIDIA's ~100-request list fetch, takes). Without
caching this cost recurs *every day*, re-resolving jobs whose location
was already known yesterday — see Caching below.

**Caching, to avoid paying that cost daily:** `data/location_cache.json`
(internal, not served, alongside `seen.json`) maps `"{company}::{job.id}"`
→ resolved location string — same company-scoped key as diffing, for the
same reason (Workday requisition IDs aren't globally unique). Before
resolving a job, check the cache first; only call the detail endpoint on
a cache miss, and only write to the cache on a successful resolution (a
timeout isn't cached, so it's retried the next run instead of staying
unresolved forever). The cache only grows — like `seen.json`, stale
entries for closed postings just sit there unused, which is harmless.
This drops the steady-state daily cost from ~455 requests to roughly
"however many *new* ambiguous postings appeared since yesterday." The
cache file must be committed by the daily-scan workflow (same as
`seen.json`) or it resets every run and defeats the point.

**Concurrency, for the remaining cold-cache cost:** even with caching, a
newly-added Workday company with many multi-location postings still pays
the resolution cost once, sequentially that would be ~2s/request. Cache
misses are resolved with a `ThreadPoolExecutor` (`RESOLVE_WORKERS = 8`)
instead of one at a time; cache hits are resolved inline with no network
call and never touch the pool. 8 was picked as "meaningfully faster
without hammering a single ATS backend too hard" — not load-tested
against Workday's actual rate limits.

Out of scope: applying this to any other ATS (none currently show the
problem); resolving locations for title-filtered-out jobs (wasted work).

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
