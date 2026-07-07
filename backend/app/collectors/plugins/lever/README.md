# Lever Collector Plugin

**Status:** Not implemented

## Purpose
Collect job listings from Lever (`jobs.lever.co`).

## Future Implementation
- Consume Lever's public JSON API
- Parse structured JSON responses
- Support company-specific subdomains

## Required Methods (BaseCollector)
- `initialize()` — Set up HTTP session
- `collect()` — Fetch and paginate Lever job listings
- `normalize()` — Map Lever JSON fields to JobData model
- `validate()` — Ensure required fields are present
- `deduplicate()` — Use Lever's unique posting ID as source_job_id
- `save()` — Persist via the shared storage interface
- `cleanup()` — Close session
