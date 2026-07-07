# Project Task Tracking (TASKS.md)

## Project Initialization Phase
- [x] Create core project files:
  - [x] `README.md`
  - [x] `PROJECT.md`
  - [x] `TASKS.md`
  - [x] `CHANGELOG.md`
  - [x] `.gitignore`
- [x] Create `AI_RULES.md` defining model contribution policies.
- [x] Establish Git Ignore rules for `.venv`, `node_modules`, `.env`, and caches.

## Phase 1: Core Foundation & API
- [x] Initialize backend FastAPI application setup.
- [x] Initialize frontend application (Vite + React + TypeScript).
- [x] Configure Ruff, Black, ESLint, Prettier, pre-commit hooks.
- [x] Create `requirements.txt`, `pyproject.toml`, `package.json`.
- [x] Create `.env.example`, `docker-compose.yml`, `Makefile`.
- [x] Design complete database data model (all 20 entities with relationships).
- [x] Create `docs/DATABASE.md` with entity dictionary, ER diagram, indexing strategy.
- [x] Build centralized configuration system with 10 domain-specific modules.
- [x] Replace flat `config.py` with modular `settings.py` + `settings/` package.
- [ ] Implement SQLAlchemy ORM models based on DATABASE.md.
- [ ] Setup Alembic migrations and DB connection strings.
- [ ] Define shared interfaces & schemas (Pydantic schema definitions).

## Phase 2: Ingestion & Scraping (Job Collector)
- [x] Build Universal Job Collector Framework (BaseCollector, registry, models, exceptions, retry, logging, config hooks).
- [x] Create plugin architecture with placeholder folders for 9 job sources.
- [x] Create collector documentation explaining lifecycle, inputs, outputs, and extension patterns.
- [x] Implement Greenhouse collector plugin (21 unit tests passing).
- [ ] Implement Playwright job scraping engine.
- [ ] Implement parsing rules for major job portals.
- [ ] Implement job details extractor & model mapping.

## Phase 3: AI Agents Subsystem
- [ ] Implement JD Analyzer Agent.
- [ ] Implement Resume Tailor Agent.
- [ ] Implement ATS Analyzer Agent.

## Phase 4: Application Automation & Tracking
- [ ] Implement Apply Agent (interactive/automated browser automation).
- [ ] Implement application status Tracker Agent.

## Phase 5: Testing & Release
- [ ] Setup backend unit testing framework.
- [ ] Run complete end-to-end integration tests.
