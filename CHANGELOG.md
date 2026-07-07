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

## [0.7.0-alpha] - 2026-07-07

### Added
- **Job API Layer:** 8 FastAPI endpoints under `/api/v1/jobs` for reading and searching job listings.
- `GET /api/v1/jobs` — Paginated list with 10 filter parameters (status, remote_type, employment_type, experience_level, salary_min, salary_max, is_active, q) and 2 sort dimensions (field + direction), including sort by company name.
- `GET /api/v1/jobs/search` — Full-text search across title, location, employment_type, and experience_level fields.
- `GET /api/v1/jobs/{id}` — Single job detail with eager-loaded company, source, and descriptions.
- `GET /api/v1/jobs/company/{company}` — Filter by company name (case-insensitive LIKE).
- `GET /api/v1/jobs/location/{location}` — Filter by location string (case-insensitive LIKE).
- `GET /api/v1/jobs/source/{source}` — Filter by source platform name (case-insensitive LIKE).
- `GET /api/v1/jobs/recent` — Most recently scraped jobs with configurable limit.
- `POST /api/v1/jobs/refresh` — Triggers all registered collectors via BackgroundTasks, returns 202 Accepted.
- **JobQueryRepository:** New query repository with 7 read methods (list_jobs, get_job_by_id, search_jobs, list_by_company, list_by_location, list_by_source, list_recent) using `selectinload` for eager relationship loading and avoiding lazy loading errors in async context.
- **API Schema Models:** `JobResponse`, `JobDetailResponse`, `CompanyResponse`, `JobSourceResponse`, `JobDescriptionResponse`, `PaginatedResponse`, `RefreshResponse`, `ErrorResponse` — all `from_attributes` enabled for ORM-to-Pydantic conversion.
- **API Dependencies:** `get_db_session` FastAPI dependency using the existing `get_session()` context manager.
- **Lifespan-based DB initialization:** `main.py` now uses FastAPI `lifespan` to call `configure()` and `create_tables()` on startup.
- **Route ordering fix:** Static routes `/search`, `/recent`, `/company/`, `/location/`, `/source/` registered before parameterized `/{job_id}` to prevent UUID validation 422 errors.
- **34 unit tests:** Full coverage for pagination, filtering, sorting, 404/422 responses, search, company/location/source lookups, recent jobs, refresh endpoint, and response shape validation.

### Fixed
- **`_ensure_async_driver` double-driver bug:** Changed `url.startswith("sqlite")` to `url.startswith("sqlite://")` — the substring `sqlite://` appears inside `aiosqlite://` causing `sqlite+aiosqlite+aiosqlite://`. Same guard applied to `postgresql://` handler.

## [0.8.0-alpha] - 2026-07-07

### Added
- **Job Collection Runner CLI:** New `backend/collect_jobs.py` entry point for running the full collector lifecycle from the command line.
- **CLI Arguments:** `--source` (filter by collector name), `--company` (pass company_name filter), `--max-pages` (override max_pages_per_source), `--dry-run` (skip save step), `--verbose` (per-stage logging), `--list-sources` (list registered collectors), `--keywords`, `--locations`, `--remote-only`, `--max-results`.
- **Collector Lifecycle Orchestration:** `_run_collector()` calls `initialize` → `collect` → `normalize` → `validate` → `deduplicate` → save (skipped in dry-run) → `cleanup` for each collector, with per-collector error isolation so one failure doesn't stop others.
- **Summary Output:** Per-collector and aggregate stats (collected, saved, duplicates skipped, errors, duration) printed on completion.
- **Error Handling:** KeyboardInterrupt, collector exceptions, and fatal errors all return proper exit codes (0 success, 1 failure).
- **22 unit tests:** Argument parsing (11 tests), collector lifecycle (3 tests), runner orchestration (5 tests), error handling (3 tests).

## [0.9.0-alpha] - 2026-07-07

### Added
- **Workday Collector Plugin:** Second concrete collector implementation extending the universal framework.
- **WorkdayCollector class:** Full BaseCollector lifecycle with `@CollectorRegistry.register` decorator, consuming the Workday Careers REST API (`POST /wday/cxs/{tenant}/{careerSite}/jobs`).
- **Workday API integration:** Pagination via `limit`/`offset`, keyword search via `searchText`, job description extraction from `jobPostingInfo.jobDescription`, location parsing from location string, remote/hybrid type detection from `bulletFields`.
- **HTTP client:** `httpx.AsyncClient` with JSON content-type, User-Agent, timeouts, and `RetryStrategy` for exponential backoff on `NetworkError` and `RateLimitError`.
- **Tenant-based routing:** Multi-company support — tenant and career site configurable via `additional_filters["tenant"]` and `additional_filters["career_site"]`, with fallback to company name.
- **Job ID extraction:** Source job ID parsed from `externalPath` regex (`_(\w+)$`) or falls back to `jobPostingId` field.
- **Bullet field parsing:** Employment type, experience level, and remote/hybrid type extracted from `bulletFields` array.
- **19 unit tests:** Full mock-based test suite with `pytest-asyncio` covering collection, pagination, max_results, empty responses, network errors, rate limits, invalid JSON, 403 error, deduplication, validation, remote/hybrid/onsite location parsing, missing fields, cleanup idempotency, job ID extraction, and tenant filtering.

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

## [0.14.0-alpha] - 2026-07-07

### Added
- **Parser Rules Engine:** New `backend/app/parsers/` package — reusable, field-level parsing rules that all collectors share. 7 built-in parsers with ParserRegistry, BaseParser base class, and ParserConfigProvider.
- **SalaryParser:** Full international salary normalization supporting INR (₹8 LPA, ₹12-18 LPA, CTC), USD ($120k, $80k-$120k, $50/hr), EUR (€70k), GBP (£50k), CAD/AUD (C$80k, A$100k). Handles ranges, single values, hourly/monthly intervals, and textual values (Competitive, Negotiable, Unknown).
- **LocationParser:** Remote/hybrid/onsite detection with country extraction for "Remote (India/Worldwide)", US state abbreviation matching, unicode city names (München), and parenthetical location tags.
- **EmploymentTypeParser:** Normalizes 7 types (full-time, part-time, contract, temporary, internship, freelance, volunteer) from 25+ synonyms (FTE, C2H, Co-op, Contractor, etc.) with remote-friendliness flag.
- **ExperienceParser:** Seniority extraction from year ranges (3-5 years → mid), min years (5+ → senior), level keywords (fresher, junior, senior, lead, principal), and French unicode support.
- **CompanyParser:** Hierarchical company/department/team/division extraction from separator-delimited strings ("Engineering > Backend > Payments Team", "Google | Cloud AI").
- **TitleParser:** Seniority prefix detection (Senior, Lead, Principal, Junior, Staff, VP) with normalized title output (seniority stripped) and role categorization.
- **MetadataParser:** Job ID extraction from URLs via 7 regex patterns, reference/requisition ID, date parsing from 14 format strings, language detection (30+ languages), and custom field passthrough.
- **ParserRegistry:** Plugin-style registration following CollectorRegistry pattern with `register()`, `get()`, `get_or_create()`, `list_parsers()`, `clear()` — adding a new parser requires one class + one register call.
- **ParsingSettings:** New `backend/app/core/settings/parsing.py` with 10 configuration groups (salary defaults, location keywords, employment synonyms, experience ranges, title stopwords, date formats) — all behavior driven from env vars with `PARSING_` prefix.
- **Configuration registration:** `Settings` loader updated with `parsing: ParsingSettings` field.
- **144 parser unit tests:** Full coverage for all 7 parsers across nominal, edge case, unicode, empty, None, malformed, synonym, normalization consistency, and registry registration paths.
- **Parser README:** Comprehensive documentation at `backend/app/parsers/README.md` covering architecture, normalization rules for each parser, extension pattern, and collector integration example.

### Changed
- `backend/app/core/settings/__init__.py`: `BaseConfig` updated from deprecated `class Config: extra = "forbid"` to modern `model_config = {"extra": "ignore"}` for pydantic v2 compatibility.

## [0.13.0-alpha] - 2026-07-07

### Added
- **LLM Client:** New `backend/app/agents/llm.py` with multi-provider support for Gemini, Groq, and Ollama — abstracts API differences behind a unified `generate()` and `generate_structured()` interface with retry logic and exponential backoff.
- **JD Analyzer Agent:** `backend/app/agents/jd_analyzer/` — extracts structured data from raw job descriptions (skills, experience requirements, tools, responsibilities, qualifications, soft skills, keywords, summary). Uses LLM when available, falls back to regex-based keyword extraction with 50+ skill/tool patterns.
- **Resume Tailor Agent:** `backend/app/agents/resume_tailor/` — rewrites resume bullet points to mirror JD terminology, reorders skills by relevance, identifies missing skills, and generates ATS-friendly markdown resumes. LLM-based with keyword fallback using action verbs and target keyword injection.
- **ATS Analyzer Agent:** `backend/app/agents/ats_checker/` — scores resume-JD compatibility (0-100) via keyword density, section-level keyword matching, readability scoring, and actionable improvement suggestions. LLM-based with statistical fallback using tokenization, bigram extraction, and section splitting.
- **Agent Data Models:** 8 new Pydantic models across agents (Skill, ExperienceRequirement, JDAnalyzerInput/Output, TailoredBullet, UserProfile, ResumeTailorInput/Output, KeywordMatch, SectionScore, ATSAnalyzerInput/Output).
- **47 unit tests:** Full test coverage for all 3 agents across both LLM and keyword-fallback code paths.

## [0.12.0-alpha] - 2026-07-07

### Added
- **Playwright Scraping Engine:** Reusable browser automation engine under `backend/app/scraping/`.
- **Modular architecture:** Five-layer design with clear separation of concerns:
  - `BrowserManager` — Playwright process start/stop, browser launch/close
  - `ContextManager` — Browser contexts (isolated sessions with cookies/cache/)
  - `PageManager` — Page CRUD, goto, reload, scroll, screenshots, HTML/title/URL getters
  - `BrowserSession` — DI-ready facade combining all managers with retry integration
  - `ScrapingEngine` — Top-level orchestrator reading from centralized config
- **Three new exception classes:** `BrowserError` and `NavigationError` extending `CollectorError` hierarchy.
- **Three new Pydantic models:** `BrowserConfig`, `SessionConfig`, `NavigationOptions` with full validation.
- **Multi-browser support:** Chromium, Firefox, and WebKit via Playwright's unified API, selected by configuration.
- **Navigation utilities:** `goto()` with wait_until/selector/scroll/screenshot options, `reload()`, `wait_for_selector()`, `wait_for_load_state()`, `wait_for_network_idle()`, `scroll_to_bottom()`, `scroll_to_element()`, `take_screenshot()`, `get_html()`, `get_title()`, `get_url()`.
- **Retry integration:** `BrowserSession.navigate()` uses `RetryStrategy` with exponential backoff for `NavigationError` and `NetworkError`.
- **Configuration from centralized layer:** All values read from `settings.playwright` and `settings.job_collection` via `CollectorConfigProvider`.
- **Dependency injection pattern:** Future collectors receive a `BrowserSession` without managing Playwright directly.
- **Resource safety:** All cleanup methods are idempotent and safe to call multiple times.
- **75 unit tests:** Full mock-based test suite covering browser initialization, context creation, page creation, navigation (success, HTTP errors, timeout, selector), reload, wait utilities, scroll, screenshots, HTML/title/URL extraction, cleanup (single, all, idempotency), error handling for all classes, configuration defaults and overrides, logging integration, dependency injection, and exception hierarchy.

## [0.11.0-alpha] - 2026-07-07

### Added
- **RemoteOK Collector Plugin:** Fifth concrete collector implementation extending the universal framework.
- **RemoteOKCollector class:** Full BaseCollector lifecycle with `@CollectorRegistry.register` decorator, consuming the RemoteOK public API (`GET https://remoteok.com/api`).
- **RemoteOK API integration:** Fetches all jobs in a single request (no pagination needed), auto-detects and skips the first metadata element returned by RemoteOK, `max_results` trimming.
- **HTTP client:** `httpx.AsyncClient` with browser-like User-Agent, timeouts, and `RetryStrategy` for exponential backoff on `NetworkError` and `RateLimitError`.
- **Response parsing:** Tags parsed from JSON string array, salary extraction (`salary_min`/`salary_max` fields with `_parse_salary` normalization), remote-type parsing from tags (`remote`/`remote only`/`worldwide`), location extraction from structured `location` field split on `/` separator, employment type inferred from tags (`full-time`, `contract`, `internship`), epoch timestamp fallback for empty `date` fields.
- **Error handling:** Rate limits, timeouts, invalid JSON, non-list responses, missing `id`/`title` fields — all captured as structured `ErrorReport` entries.
- **Edge case coverage:** Empty responses, metadata-only responses, `max_results` trimming, validation rejection of incomplete jobs (missing title, missing url), deduplication against `existing_source_ids`, missing field resilience, jobs without IDs skipped.
- **32 unit tests:** Full mock-based test suite with `pytest-asyncio` covering collection, metadata skipping, normalization, validation, deduplication, error recovery (network, rate limit, timeout), JSON parsing, tag extraction (JSON string, empty string, invalid JSON), salary parsing (range, zero, min-only), location parsing (multi-segment, remote), employment type inference, cleanup idempotency, registry integration, and epoch date fallback.

## [0.19.0-alpha] - 2026-07-07

### Added
- **Premium Dashboard Page:** Fully redesigned dashboard with 8 premium sections comparable to Linear/Vercel/Stripe quality.
- **Welcome Header:** Time-based greeting ("Good morning/afternoon/evening"), current date, user avatar with initials, glassmorphism backdrop, quick search bar with Cmd+K hint.
- **Animated Statistics Cards:** 8 stat cards (Total Jobs, Applied, Saved, Interviews, Offers, Rejections, Resume Score, ATS Score) with framer-motion scroll-triggered animated counters and trend indicators. Full responsive grid layout.
- **AI Insights Panel:** 6 insight cards (Resume Improvement, ATS Suggestions, Market Trends, Missing Skills, Salary Insights, Demand Skills) with priority-colored left borders, SVG circular score indicators, and action buttons. 3x2 responsive grid with stagger animations.
- **Premium Recent Jobs Table:** Card-based premium table with search filtering, sortable columns (title, company, salary, date), salary formatting, relative timestamps, status badges. Framer Motion stagger row animations.
- **Applications Timeline:** Vertical timeline with 6 events (interview, application, offer, rejection, assessment, saved). Type-colored icon circles, connecting line, alternating left/right layout on desktop, status badges, relative times. Sequential stagger animation.
- **Quick Actions Grid:** 6 action cards (Apply to Jobs, Analyze Resume, Tailor Resume, Import Resume, Refresh Jobs, Open Tracker) with dynamic lucide-react icons, colored accents, hover lift effects. Linked to respective pages via React Router.
- **Market Overview Charts:** 3 pure CSS/SVG chart panels (Skills Demand horizontal bars, Applications Trend vertical bars, Salary Trend SVG line chart). Scroll-triggered bar and line animations. No external chart library dependency.
- **Notifications Panel:** 6 notification items with type-based icons (activity/system/recommendation), unread blue dot indicators, relative timestamps, "Mark all read" action, stagger animations.
- **StatusBadge Component:** Maps all 16 ApplicationStatus values to appropriate Badge variants (success/warning/destructive/info/default) with lucide-react icons.
- **AnimatedCounter Component:** Reusable framer-motion scroll-triggered number counter with configurable prefix, suffix, decimals, duration, and easing.
- **8 New Dashboard Types:** DashboardStats, DashboardStat, InsightCard, TimelineEvent, QuickAction, ChartDataPoint, MarketData, DashboardNotification — prepared for future backend integration.
- **Mock Data Module:** 7 complete mock datasets (stats, trends, insights, timeline events, quick actions, market data, notifications, recent jobs) with realistic values for Stripe, Vercel, Linear, Notion, Cursor, Datadog, and Google.

## [0.18.0-alpha] - 2026-07-07

### Added
- **Frontend Foundation:** Premium SaaS-grade frontend built with React 19, TypeScript, Vite, TailwindCSS v4, Framer Motion, and shadcn/ui design patterns.
- **Theme System:** Full dark/light/system theme with CSS custom properties, automatic system preference detection, and localStorage persistence via Zustand. 40+ semantic color tokens for background, foreground, card, primary, secondary, muted, accent, destructive, sidebar, success, warning, and info — all with dark mode variants.
- **Complete shadcn-style UI Component Library:** 20 handcrafted components from Radix primitives + class-variance-authority:
  - Button (6 variants, 4 sizes, loading state, asChild support)
  - Input, Textarea, Card, Badge (6 variants, 3 sizes), Avatar (4 sizes), Skeleton
  - Dialog (framer-motion scale/fade animations, glassmorphism overlay)
  - DropdownMenu (full system with submenus, separators, shortcuts, groups)
  - Tabs, Table, Select, Checkbox, RadioGroup, Accordion, Separator, Progress
  - Toast (with use-toast hook and standalone toast() function)
  - Tooltip, Drawer (left/right placement with spring animations)
- **Application Layout:** Animated collapsible sidebar (280px/64px width transition) with 9 navigation items, active route highlighting, tooltips for collapsed state, mobile overlay drawer. Top nav with search bar (Cmd+K hint), theme toggle, notification bell with badge, and profile dropdown menu. Animated page transitions via Framer Motion AnimatePresence.
- **4 Zustand Stores:** `auth-store` (user, login/logout, token management), `theme-store` (light/dark/system with system change listener), `sidebar-store` (collapse, mobile, resize state), `notification-store` (queue, unread count, auto-dismiss).
- **6 Custom Hooks:** `useAuth`, `useTheme` (class toggling + media query listener), `useMediaQuery`, `useKeyboardShortcut`, `useNotifications` (auto-dismiss with ref-guarded timers), `useAuthContext`.
- **5 Shared Components:** `PageHeader` (animated title/description/actions), `EmptyState` (fade+scale with icon and action), `ErrorState` (wobbling alert icon with retry), `StatCard` (glassmorphism card with hover lift and trend indicators), `LoadingScreen` (pulsing logo + animated dots).
- **11 Page Shells:** Dashboard (4 stat cards + recent activity empty state), Jobs, Resume, ATS Analyzer, AI Tailor, Applications (status filter tabs), Tracker, Analytics, Settings (profile/notifications/appearance sections), NotFound (animated 404).
- **Provider Tree:** `ThemeProvider`, `QueryProvider` (TanStack Query with 30s staleTime), `AuthProvider` (auto-check on mount with loading spinner).
- **React Router:** Nested routes under `AppLayout` with lazy page transitions, automatic redirect `/` → `/dashboard`.
- **API Layer:** Axios client with baseURL `/api/v1`, auth token injection, 401 redirect, timeout. Typed CRUD helpers (`getPaginated`, `getById`, `create`, `update`, `remove`). Job service with search params interface.
- **CSS Utilities:** Custom animations (fadeIn, slideInRight, slideInBottom, scaleIn, shimmer), custom scrollbar styling, skeleton shimmer keyframe, cn() helper with tailwind-merge + clsx.
- **Build:** Zero TypeScript errors, 2415 modules bundled, 43.73 KB CSS + 613.69 KB JS (gzip: 8.19 KB + 196.63 KB).

## [0.17.0-alpha] - 2026-07-07

### Added
- **End-to-End Integration Tests:** New `tests/test_integration.py` with 41 tests spanning 9 verification categories:
  - Backend startup (FastAPI app creation, health endpoint)
  - Database initialization (session management, full CRUD across 4 models)
  - Job API endpoints (10 tests: list, pagination, get-by-id, 404, search, filter, recent, company/location/source lookup)
  - Collector pipeline (registry discovery, collector class lookup, JobData-to-model mapping)
  - AI agents (JD Analyzer, Resume Tailor, ATS Analyzer — all keyword-fallback paths; LLM client creation)
  - Apply Agent (state machine transitions, invalid transition rejection, field mapper, validation imports)
  - Tracker Agent (full lifecycle, duplicate detection, apply result recording, invalid transitions, cleanup)
  - Parser/extractor pipeline (all 7 parsers + registry + metadata extractor)
  - Cross-component (API returns related data, tracker reads job from DB, full job→tracker pipeline)
- **Phase 5 completion:** All end-to-end integration tests passing (41 tests, 0 failures).

### Changed
- **TASKS.md:** Marked `Run complete end-to-end integration tests` as completed (Phase 5 done).

## [0.16.0-alpha] - 2026-07-07

### Added
- **Apply Agent Framework:** New `backend/app/agents/apply_agent/` package — reusable browser automation for job application form submission across any portal.
- **16 files, 103 unit tests, 0 dependencies on existing component changes.**
- **State Machine** (`state_machine.py`): 10-state finite state machine (`initialized` → `page_loaded` → `analyzed` → `filled` → `uploaded` → `reviewed` → `submitted` → `verified`, with `failed` and `cancelled` terminal states). Validated transitions with history tracking.
- **Form Detection** (`form_detector.py`): Detects `<input>`, `<select>`, `<textarea>` elements via Playwright locator APIs. Extracts labels via 5 strategies (aria-label, `<label for>`, parent label, placeholder, name). Builds unique CSS selectors, sorts by tab order, deduplicates. 3 element role maps covering input types, autocomplete attributes, and ARIA roles.
- **Field Mapping** (`field_mapper.py`): Maps detected fields to 40+ canonical types using 350+ regex patterns grouped by type. Checks autocomplete first (most reliable), then label, placeholder, and name attribute. Unknown fields get fallback `field_` keys. Includes patterns for name, email, phone, address, company, job title, linkedin, portfolio, education, skills, salary, visa, veteran, disability, EEO, consent, and more.
- **Field Fillers** (`field_fillers.py`): Fills text inputs/dropdowns/checkboxes/radio buttons/date pickers with appropriate Playwright APIs. Dropdown fill tries exact label, exact value, partial match, first non-empty option. Batch `fill_all()` method returns per-field errors.
- **Resume Uploader** (`resume_uploader.py`): Playwright file chooser API for PDF/DOCX/DOC/TXT/RTF upload. Supports absolute and storage-relative paths. Uploads to first file input or a specific field selector.
- **Cover Letter Generator** (`cover_letter_generator.py`): Two strategies — delegates to ResumeTailorAgent when registered, falls back to a template-based approach. Writes to output files with automatic naming.
- **Question Answerer** (`question_answerer.py`): Five-strategy question answering (standard map → user profile → JD Analyzer → LLM → safe fallback). Classifies questions using FieldMapper patterns. Answers all detected questions in batch.
- **Submit Handler** (`submit_handler.py`): Three modes: `review` (pre-filled screenshot, no submission), `dry_run` (full fill + screenshot, no submit), `submit` (actual submission with confirmation detection). Find submit button via 11 CSS strategies. Verification extracts confirmation/reference codes via 3 regex patterns. Error detection after submission.
- **Application Session** (`application_session.py`): Wraps BrowserSession with navigation, load waiting, screenshot, and cleanup. Tracks navigation count. Safe `close()` — idempotent and exception-safe. Async context manager support.
- **Validation** (`validation.py`): Pre-flight checks for each lifecycle step. Validates user profile completeness, form field constraints, required field coverage, and file path formats.
- **Exception Hierarchy** (`exceptions.py`): 10 typed exceptions: `ApplyError` (base), `NavigationError`, `FormDetectionError`, `FieldFillError`, `UploadError`, `SubmissionError`, `VerificationError`, `ValidationError`, `StateTransitionError`, `TimeoutError`, `UnsupportedFormError`, `BrowserCleanupError`.
- **ApplyAgent Orchestrator** (`apply_agent.py`): Runs 8-step lifecycle (navigate → analyze → fill → upload → cover letter → questions → submit → verify). Manages sub-component creation (FormDetector, FieldMapper, FieldFiller, ResumeUploader, CoverLetterGenerator, QuestionAnswerer, SubmitHandler). Supports external agent injection (ResumeTailor, JDAnalyzer). Returns `ApplicationResult` with summary, confirmation code, screenshots, state history, and duration.
- **Data Models:** `ApplicationContext` (per-run state), `ApplicationResult` (structured output), `FormField` (detected form element), `UserProfile` (applicant data), `UploadedDocument` (upload result). All dataclass-based with sensible defaults.
- **103 unit tests:** Full coverage for state machine (10 tests), data models (6 tests), exceptions (7 tests), validation (10 tests), form detection (5 tests), field mapping (7 tests), field fillers (5 tests), resume uploader (5 tests), cover letter generator (4 tests), question answerer (8 tests), submit handler (8 tests), application session (7 tests), apply agent (7 tests), and integration scenarios (14 tests).

## [0.10.0-alpha] - 2026-07-07

### Added
- **Ashby Collector Plugin:** Fourth concrete collector implementation extending the universal framework.
- **AshbyCollector class:** Full BaseCollector lifecycle with `@CollectorRegistry.register` decorator, consuming the Ashby public REST API (`GET https://api.ashbyhq.com/posting-api/job-board/{boardToken}?includeCompensation=true`).
- **Ashby API integration:** Single-request collection (no pagination needed — Ashby returns all jobs at once), `isListed` filtering to exclude draft/unlisted postings, department mapped to skills array, compensation parsing from `compensationSummary` field.
- **HTTP client:** `httpx.AsyncClient` with User-Agent, timeouts, and `RetryStrategy` for exponential backoff on `NetworkError` and `RateLimitError`.
- **Response parsing:** Location parsing (city/state/country/remote/dash-separated formats), compensation extraction (single and range values, USD/EUR/GBP currency detection, hourly/monthly/yearly interval inference), HTML-to-text description conversion.
- **Error handling:** 404 boards, rate limits, timeouts, invalid JSON, non-dict responses, missing `jobs` field — all captured as structured `ErrorReport` entries.
- **Edge case coverage:** Empty responses, `max_results` trimming, `isListed` filtering, validation rejection of incomplete jobs, deduplication against `existing_source_ids`, unlisted job exclusion, missing field resilience.
- **28 unit tests:** Full mock-based test suite with `pytest-asyncio` covering collection, isListed filtering, normalization, validation, deduplication, error recovery (network, rate limit, 404, timeout, parsing), compensation parsing (range, single, hourly interval, currency), location parsing (city/state, remote, dash-separated), missing fields, cleanup idempotency, registry integration, and board token routing.
