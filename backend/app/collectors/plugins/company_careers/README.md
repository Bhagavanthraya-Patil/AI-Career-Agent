# Company Career Pages Collector Plugin

**Status:** Not implemented

## Purpose
Collect job listings directly from company career pages (non-ATS portals).

## Future Implementation
- Maintain a registry of company career page URLs
- Use Playwright to scrape each company's career page
- Handle diverse HTML structures across different companies
- Implement site-specific parsers for common career page layouts

## Required Methods (BaseCollector)
- `initialize()` — Launch Playwright browser
- `collect()` — Navigate to career pages and scrape listings
- `normalize()` — Map diverse HTML structures to JobData model
- `validate()` — Ensure required fields are present
- `deduplicate()` — Use company+title+location hash as source_job_id
- `save()` — Persist via the shared storage interface
- `cleanup()` — Close browser and context
