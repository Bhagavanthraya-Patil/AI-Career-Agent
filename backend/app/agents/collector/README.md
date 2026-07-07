# backend/app/agents/collector

Job Collector Agent — searches, scrapes, and aggregates job listings from platforms (LinkedIn, Indeed, Glassdoor, Greenhouse, Lever, etc.).

## Responsibilities

- Execute parameterized searches based on user criteria (keywords, location, salary)
- Scrape structured job data via Playwright headless browser
- Deduplicate and normalize job listings
- Persist discovered jobs to the Jobs table

## Input

User query profile (e.g., "Remote Python Developer", location filters, salary range)

## Output

Structured list of jobs added to the `Jobs` database table
