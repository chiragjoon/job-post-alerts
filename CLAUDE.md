# Project: job-post-alerts

## What this is

A single-user personal job alert tool. You maintain a config file listing company careers page URLs plus job title/location filters. A daily GitHub Actions run detects each site's ATS (Greenhouse, Lever, Ashby, etc.), fetches current job postings, filters them against your criteria, and publishes the results to a static page you check daily. No email, no accounts, no database — just a config file and a page.

## Stack

- Python for the scraper/filter logic (ATS detection, per-ATS adapters, filtering)
- GitHub Actions for the daily scheduled run (cron) and committing updated results
- Static HTML/JS frontend (GitHub Pages) reading a committed `jobs.json` as its data source

## Planning

See docs/PLAN.md for the approved project plan.

## Conventions

- [add as you go — naming, folder structure, style choices]

## Things Claude got wrong before (don't repeat)

- [whenever you correct something mid-project, write the correction here]
