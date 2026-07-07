# Ashby Collector Plugin

**Status:** Not implemented

## Purpose
Collect job listings from Ashby-powered career pages.

## Future Implementation
- Consume Ashby's public GraphQL API
- Parse structured JSON responses
- Support company-specific Ashby instances

## Required Methods (BaseCollector)
- `initialize()` — Set up HTTP session and API client
- `collect()` — Query Ashby API with search parameters
- `normalize()` — Map Ashby fields to JobData model
- `validate()` — Ensure required fields are present
- `deduplicate()` — Use Ashby's job ID as source_job_id
- `save()` — Persist via the shared storage interface
- `cleanup()` — Close session
