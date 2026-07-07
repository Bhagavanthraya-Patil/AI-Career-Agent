# Wellfound (AngelList) Collector Plugin

**Status:** Not implemented

## Purpose
Collect startup job listings from Wellfound (formerly AngelList Talent).

## Future Implementation
- Use Playwright-based browser automation
- Parse startup-focused job listings with equity/salary details
- Handle Wellfound's unique startup culture filters

## Required Methods (BaseCollector)
- `initialize()` — Launch Playwright browser or set up HTTP session
- `collect()` — Search Wellfound and scrape listings
- `normalize()` — Map Wellfound fields to JobData model
- `validate()` — Ensure required fields are present
- `deduplicate()` — Use Wellfound's listing ID as source_job_id
- `save()` — Persist via the shared storage interface
- `cleanup()` — Close browser/session
