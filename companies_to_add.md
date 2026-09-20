# Companies to add

Add one row per company below, then run:

    python3 -m src.bulk_add_companies

Each row gets the same validation as `src.add_company` (ATS detection +
a live test fetch) before it's added. Rows that succeed are removed from
this file automatically. Rows that fail (bad URL, duplicate) are left
here untouched, with the reason printed to the console — fix the URL and
rerun without retyping the rest.

Example row: `| Airbnb | https://careers.airbnb.com |`

| Name | Careers URL |
| --- | --- |
| Beacon | https://job-boards.greenhouse.io/beacon67 |
| Robin AI | https://jobs.ashbyhq.com/robin-ai |

## Notes on this batch (2026-09-20)

Skipped entirely — no usable board found, or explicitly declined:
- **HashiCorp** — acquired by IBM; careers now route through IBM's WAF-protected site, no ATS this repo supports.
- **dbt Labs** — merged into Fivetran; dbt-specific roles now live inside the Fivetran board already listed above (filter by "dbt" in the title if you want just those).
- **Snyk** — old Greenhouse board is dead; couldn't confirm their current (likely Workday) tenant/site.
- **Tessian** — acquired by Proofpoint; no separate board found, and Proofpoint's own board wasn't researched.
- **Bloomberg** — Bloomberg L.P./Terminal uses Avature (unsupported); declined tracking the separate Bloomberg Industry Group Workday board instead.
- **FloodFlash** — uses Breezy HR (unsupported), and the board currently 404s anyway.
- **Peak** (Peak AI) — acquired by UiPath; no dedicated board found.
- **Payload** — too ambiguous to identify the intended company; skipped per your call.

Added with caveats — worth knowing before you rely on these:
- **Onfido (Entrust)** and **Featurespace (Visa)** point at their acquirer's full company-wide Workday board (not isolated to the original team) — your `["Engineer"]` title filter will narrow it down, but matches won't necessarily be relevant to identity-verification/fraud work specifically.
- **S&P Global Market Intelligence** points at S&P Global's one company-wide Workday board (no MI-only filter exists).
- **Ravelin**, **Wiz**, **Beacon** — real, live boards that currently have 0 open roles. They'll add fine but won't surface anything until they post.
- **Concirrus**, **Radancy**, **Arbolus**, **Zencargo** — not on a supported ATS (BambooHR, in-house, Teamtailor-on-a-custom-domain, and Pinpoint respectively). Left in so `bulk_add_companies` can try the generic scraper; expect these to fail or return nothing, in which case they'll stay in this file with a reason printed.
- **Metapack** uses the **Auctane** (its parent) Greenhouse token — a dedicated `metapack` token exists but is empty.
- **Kraken**'s Ashby token is literally `kraken.com` (with the dot) — this is the crypto exchange, not Kraken Technologies.
- **SentinelOne**'s Greenhouse token is `sentinellabs` (their original name), not `sentinelone`.
- **Isidor** is a ~4-person pre-seed startup — re-check this board periodically in case it changes ATS.