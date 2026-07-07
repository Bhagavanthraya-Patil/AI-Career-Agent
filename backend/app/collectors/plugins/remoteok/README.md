# RemoteOK Collector Plugin

**Status:** Not implemented

## Purpose
Collect remote job listings from RemoteOK.

## Future Implementation
- Consume RemoteOK's public API
- Parse structured JSON responses
- Focus on remote-specific job filters

## Required Methods (BaseCollector)
- `initialize()` — Set up HTTP session
- `collect()` — Fetch RemoteOK API with search parameters
- `normalize()` — Map RemoteOK fields to JobData model
- `validate()` — Ensure required fields are present
- `deduplicate()` — Use RemoteOK's listing ID as source_job_id
- `save()` — Persist via the shared storage interface
- `cleanup()` — Close session
