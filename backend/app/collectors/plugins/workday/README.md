# Workday Collector Plugin

**Status:** Not implemented

## Purpose
Collect job listings from Workday-powered career portals.

## Future Implementation
- Parse Workday XML/JSON API responses
- Handle Workday's unique URL structure (`myworkdayjobs.com`)
- Support tenant-specific scraping across different companies using Workday

## Required Methods (BaseCollector)
- `initialize()` — Set up HTTP session with Workday cookies
- `collect()` — Search and paginate through Workday listings
- `normalize()` — Map Workday fields to JobData model
- `validate()` — Ensure required fields are present
- `deduplicate()` — Use Workday's `jobPostingId` as source_job_id
- `save()` — Persist via the shared storage interface
- `cleanup()` — Close session
