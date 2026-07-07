# Greenhouse Collector Plugin

**Status:** Not implemented

## Purpose
Collect job listings from Greenhouse (`boards.greenhouse.io`).

## Future Implementation
- Consume Greenhouse's public JSON API at `/boards/{board_token}/jobs`
- Parse structured JSON responses directly
- Support board token discovery

## Required Methods (BaseCollector)
- `initialize()` — Set up HTTP session
- `collect()` — Fetch and paginate Greenhouse job listings
- `normalize()` — Map Greenhouse JSON fields to JobData model
- `validate()` — Ensure required fields are present
- `deduplicate()` — Use Greenhouse's `id` or `absolute_url` as source_job_id
- `save()` — Persist via the shared storage interface
- `cleanup()` — Close session
