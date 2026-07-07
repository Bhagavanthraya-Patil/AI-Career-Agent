# LinkedIn Collector Plugin

**Status:** Not implemented

## Purpose
Collect job listings from LinkedIn Jobs.

## Future Implementation
- Use Playwright-based browser automation for LinkedIn Jobs search
- Handle LinkedIn's anti-bot protections and login flow
- Parse job cards and detail pages from the DOM

## Required Methods (BaseCollector)
- `initialize()` — Launch Playwright browser, set up stealth
- `collect()` — Search LinkedIn Jobs and scrape listings
- `normalize()` — Map scraped fields to JobData model
- `validate()` — Ensure required fields are present
- `deduplicate()` — Use LinkedIn's job posting ID as source_job_id
- `save()` — Persist via the shared storage interface
- `cleanup()` — Close browser and context
