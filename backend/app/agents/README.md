# backend/app/agents

AI agent orchestration layer. Each subdirectory represents a self-contained agent with a single responsibility, following the modular agent design principle.

## Agents

- `collector/` — Job Collector Agent: scrapes and ingests job listings
- `jd_analyzer/` — JD Analyzer Agent: parses and extracts structured data from job descriptions
- `resume_tailor/` — Resume Tailor Agent: aligns work history with target job keywords
- `ats_checker/` — ATS Analyzer Agent: scores resume-JD similarity and suggests improvements
- `cover_letter/` — Cover Letter Agent: generates tailored cover letters
- `apply_agent/` — Apply Agent: automates form filling and application submission
- `tracker/` — Tracker Agent: monitors application status and updates pipeline
