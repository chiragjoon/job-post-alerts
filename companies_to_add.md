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
|---|---|
