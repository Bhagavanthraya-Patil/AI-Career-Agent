# automation/playwright

Playwright browser automation scripts for web scraping and application form filling.

## Contents

- `scrapers/` — Job platform scrapers (LinkedIn, Indeed, Glassdoor, Greenhouse, Lever)
- `form_fillers/` — Auto-fill logic for standard application forms
- `stealth/` — Anti-detection utilities (randomized delays, user agents, viewports)
- `utils/` — Shared browser helpers and page interaction utilities

## Principles

- Mimic human interaction with randomized delays and scroll speeds
- Use stealth mode configurations to bypass bot detection
- Execute in sandboxed processes with limited file system access
