# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0-alpha] - 2026-07-07

### Added
- Created `PROJECT.md` specifying complete vision, scope, stack, folder structures, milestones, and high-level agentic architectures.
- Created `AI_RULES.md` defining strict constraints, standards, coding policies, and handoff rules for AI assistants.
- Configured `.gitignore` to prevent committing virtual environments, node modules, build files, environments, and caches.
- Initialized empty tracker documents: `CHANGELOG.md` and `TASKS.md` (now fully structured and updated).
- Verified existing base `README.md`.

## [0.2.0-alpha] - 2026-07-07

### Added
- **Backend Initialization:** FastAPI application scaffold with `main.py`, health check endpoint, and Pydantic `Settings` via `pydantic-settings`.
- **Python Packaging:** `requirements.txt` with pinned dependencies (FastAPI, SQLAlchemy, Alembic, Playwright, google-genai, etc.) and `pyproject.toml` with Ruff/Black/pytest configuration.
- **Package Structure:** `__init__.py` files across all `backend/app/` subpackages (agents, api, core, db, schemas, services, tests).
- **Frontend Initialization:** Vite + React + TypeScript scaffold with `package.json`, `tsconfig.json` (strict mode), `vite.config.ts` (with API proxy), `index.html`, `main.tsx`, and `App.tsx` placeholder.
- **Frontend Linting:** ESLint config with TypeScript strict rules (`no-explicit-any` as error) and Prettier formatting config.
- **Dev Tooling:** `Makefile` with common commands (setup, dev, lint, format, test, clean), `.pre-commit-config.yaml` with Ruff, Black, Prettier, and standard hooks, and `.env.example` documenting all required environment variables.
- **Containerization:** `docker-compose.yml` for backend and frontend services (optional — not required for local dev).

## [0.3.0-alpha] - 2026-07-07

### Added
- **Data Model Design:** Complete database architecture documented in `docs/DATABASE.md` covering all 20 entities.
- **Entity Dictionary:** Detailed specifications for `users`, `user_profiles`, `master_resumes`, `resume_versions`, `job_sources`, `companies`, `jobs`, `job_descriptions`, `skills`, `keywords`, `ats_analyses`, `resume_analyses`, `cover_letters`, `applications`, `application_status_history`, `interviews`, `ai_generations`, `workflow_executions`, `settings`, and `logs`.
- **Mermaid ER Diagram:** Visual entity-relationship diagram in `docs/DATABASE.md` showing all table relationships and cardinalities.
- **PostgreSQL Optimization:** UUID primary keys, TIMESTAMPTZ, JSONB for flexible data, proper many-to-many join tables (`job_skills`, `job_keywords`, `resume_version_skills`, `resume_version_keywords`).
- **SaaS Readiness:** `tenant_id` column on `users` table for future multi-tenant row-level security, plus exploration of all entities for scalability notes.
- **Indexing Strategy:** 13 recommended indexes defined per query pattern.
- **Immutable Audit Trail:** `application_status_history` as a separate table for status change tracking; `ai_generations` as audit log for every LLM invocation.

## [0.4.0-alpha] - 2026-07-07

### Added
- **Centralized Configuration System:** Replaced flat `config.py` with a modular `settings.py` + `settings/` package architecture using `pydantic-settings`.
- **10 Domain-Specific Config Modules:**
  - `app` — Application metadata, environment detection, CORS origins, API binding
  - `database` — Connection URL, pool sizing, echo logging, migration-on-start flag
  - `gemini` — Multi-provider LLM config (Gemini, Groq, Ollama) with provider-level validation and cache TTL
  - `playwright` — Browser type, viewport, stealth mode, rate limiting, retry/backoff
  - `logging_settings` — Level, format (json/text), output destination, structured agent trace path
  - `email` — IMAP/Gmail API config for application status monitoring (disabled by default)
  - `storage` — Base paths for resumes, jobs, logs; file size limits; allowed formats
  - `job_collection` — Daily limits, scrape delays, retry policies, source enablement, proxy support
  - `application` — Submission limits, review requirements, experimental auto-submit, form field fill toggles
- **Environment Variable Naming Convention:** All vars follow `{SECTION}_{FIELD}` pattern (e.g., `DATABASE_URL`, `GEMINI_GEMINI_API_KEY`, `PLAYWRIGHT_HEADLESS`) for clarity.
- **Validation:** Required API key validation per selected LLM provider via Pydantic `model_validator`.
- **`.env.example`:** Comprehensive template documenting every configuration option with defaults and comments.
- **Settings Archive:** Old flat `backend/app/core/config.py` deleted; `backend/main.py` updated to import from `app.core.settings`.

## [0.6.0-alpha] - 2026-07-07

### Added
- **Greenhouse Collector Plugin:** First concrete collector implementation extending the universal framework.
- **GreenhouseCollector class:** Full BaseCollector lifecycle (initialize, collect, normalize, validate, deduplicate, save, cleanup) with `@CollectorRegistry.register` decorator.
- **Greenhouse JSON API integration:** Consumes `GET https://api.greenhouse.io/v1/boards/{board_token}/jobs?content=true&page=N` with pagination, content extraction, and metadata parsing.
- **HTTP client:** `httpx.AsyncClient` with User-Agent, timeouts, and `RetryStrategy` for exponential backoff on `NetworkError` and `RateLimitError`.
- **Response parsing:** Location parsing (city/state/country/remote detection), salary extraction from metadata, employment type and experience level mapping, HTML-to-text description conversion.
- **Error handling:** 404 boards, rate limits, timeouts, invalid JSON — all captured as structured `ErrorReport` entries.
- **Edge case coverage:** Empty responses, pagination boundary conditions, `max_results` trimming, validation rejection of incomplete jobs, deduplication against `existing_source_ids`.
- **21 unit tests:** Full mock-based test suite with `pytest-asyncio` covering collection, normalization, validation, deduplication, error recovery, location parsing, salary parsing, cleanup idempotency, and registry integration.

## [0.5.0-alpha] - 2026-07-07

### Added
- **Universal Job Collector Framework:** Modular, extensible job collection system under `backend/app/collectors/`.
- **BaseCollector Abstract Class:** Defines the standard collector lifecycle (`initialize` → `collect` → `normalize` → `validate` → `deduplicate` → `save` → `cleanup`) with a guaranteed `execute()` orchestration method and `cleanup()` finally-block safety.
- **CollectorRegistry:** Auto-discovery of collector implementations via package scanning and decorator-based registration. No hardcoded collector references.
- **Data Models (Pydantic):** `CollectorQuery`, `JobData`, `CompanyData`, `LocationData`, `SalaryData`, `JobMetadata`, `CollectorResult`, `CollectionStats`, `ErrorReport` — fully typed with field descriptions.
- **Exception Hierarchy:** `CollectorError` base with `AuthenticationError`, `RateLimitError` (with `retry_after`), `ParsingError`, `ValidationError` (with `field`/`value`), `StorageError`, `NetworkError` (with `status_code`).
- **Retry Framework:** `RetryStrategy` class and `@retry` decorator supporting configurable max_retries, exponential backoff, capped delay, per-call timeout, cancellation propagation, and RateLimitError `retry_after` integration.
- **Logging Interface:** `CollectorLoggerProtocol` — structural typing (Protocol) with `info`, `warning`, `error`, `debug` methods. No logging provider implementation.
- **Configuration Hooks:** `CollectorConfigProvider` reads from the centralized `settings.job_collection`, `settings.playwright`, and `settings.storage` namespaces. All values from environment — no hardcoded defaults.
- **Lifecycle Documentation:** `CollectorStage` and `CollectorState` enums plus documented stage ordering and guarantees.
- **Plugin Folders:** 9 future collector placeholder packages with READMEs (`workday`, `greenhouse`, `lever`, `ashby`, `linkedin`, `google_jobs`, `wellfound`, `remoteok`, `company_careers`).
- **Full Documentation:** `backend/app/collectors/README.md` explaining step-by-step collector creation, required methods, expected inputs/outputs, data models, exception hierarchy, retry usage, and configuration integration.
