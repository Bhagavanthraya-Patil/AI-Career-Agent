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
- [x] Implement SQLAlchemy ORM models based on DATABASE.md.
- [x] Setup Alembic migrations and DB connection strings.
- [x] Define shared interfaces & schemas (Pydantic schema definitions).
- [x] Implement Job API layer (8 endpoints, pagination, sorting, filtering, search).
- [x] Create JobQueryRepository for read/list/search operations.
- [x] Register job API router with lifespan-based DB configuration in main.py.
- [x] Write 34 unit tests for all Job API endpoints.

## Phase 2: Ingestion & Scraping (Job Collector)
- [x] Build Universal Job Collector Framework (BaseCollector, registry, models, exceptions, retry, logging, config hooks).
- [x] Create plugin architecture with placeholder folders for 9 job sources.
- [x] Create collector documentation explaining lifecycle, inputs, outputs, and extension patterns.
- [x] Implement Greenhouse collector plugin (21 unit tests passing).
- [x] Implement Workday collector plugin (19 unit tests passing).
- [x] Create CLI entry point for job collection runner (`collect_jobs.py` with --source, --dry-run, --verbose, --company, --max-pages, --list-sources flags; 22 unit tests).
- [x] Implement Lever collector plugin (21 unit tests passing).
- [x] Implement Ashby collector plugin (28 unit tests passing).
- [x] Implement RemoteOK collector plugin (32 unit tests passing).
- [x] Implement Playwright job scraping engine (75 unit tests passing).
- [x] Build reusable Parser Rules Engine under `app/parsers/`:
  - [x] BaseParser abstract class with Generic[T] type support
  - [x] ParserRegistry with plugin registration and instance caching
  - [x] SalaryParser — INR (LPA/CTC), USD ($k), EUR/GBP, hourly/monthly, textual (Competitive)
  - [x] LocationParser — remote/hybrid/onsite, country extraction, US states, unicode cities
  - [x] EmploymentTypeParser — full-time, part-time, contract, internship, freelance, synonyms
  - [x] ExperienceParser — fresher, year ranges, min years, seniority keywords, French unicode
  - [x] CompanyParser — hierarchy with separators (> / | -), department/team/business unit
  - [x] TitleParser — seniority prefix detection, role normalization, stopword stripping
  - [x] MetadataParser — job IDs from URLs, reference IDs, dates (14 formats), language, custom
  - [x] ParserConfigProvider — all behavior from centralized ParsingSettings
  - [x] ParsingSettings with 10 domain-specific configuration groups
  - [x] 144 unit tests covering all parsers, registry, normalization, edge cases, unicode
  - [x] Full README documentation with architecture, normalization rules, extension pattern
- [x] Implement job details extractor & model mapping (73 tests).

## Phase 3: AI Agents Subsystem
- [x] Create LLM client with Gemini/Groq/Ollama provider support and retry logic.
- [x] Implement JD Analyzer Agent with LLM-based extraction and keyword fallback.
- [x] Implement Resume Tailor Agent with LLM-based tailoring and keyword fallback.
- [x] Implement ATS Analyzer Agent with LLM-based scoring and keyword fallback.
- [x] Write 47 unit tests for all 3 agents (keyword fallback + LLM paths).

## Phase 4: Application Automation & Tracking
- [x] Implement Apply Agent (reusable browser automation framework):
  - [x] State machine (10 states, validated transitions, history tracking)
  - [x] Form detection (Playwright locator APIs + heuristics)
  - [x] Field mapping (regex patterns → 40+ canonical types)
  - [x] Field fillers (text, dropdown, checkbox, radio, date)
  - [x] Resume uploader (Playwright file chooser API, PDF/DOCX)
  - [x] Cover letter generator (ResumeTailorAgent delegation + template fallback)
  - [x] Question answerer (standard map, profile, JD Analyzer, LLM, safe fallback)
  - [x] Submit handler (review/dry_run/submit modes, confirmation detection)
  - [x] Application session (Playwright session lifecycle wrapper)
  - [x] Application context (per-run state, form fields, user profile)
  - [x] Validation (pre-flight checks, field validation, file validation)
  - [x] ApplyAgent orchestrator (full lifecycle with state machine)
  - [x] Exceptions (10 typed exception classes)
  - [x] 103 unit tests for all 16 files
- [ ] Implement application status Tracker Agent.

## Phase 5: Testing & Release
- [x] Setup backend unit testing framework.
- [x] Run complete end-to-end integration tests.

## Phase 6: Frontend Foundation
- [x] Install and configure dependencies (TailwindCSS v4, Framer Motion, TanStack Query, Axios, React Router, shadcn/radix, React Hook Form, Zod).
- [x] Configure Vite path aliases (`@/` → `./src/`), TailwindCSS v4 with `@tailwindcss/vite` plugin, TypeScript paths.
- [x] Build complete shadcn-style UI component library (20 components).
- [x] Implement Zustand stores (auth, theme, sidebar, notifications).
- [x] Build provider tree (ThemeProvider, QueryProvider, AuthProvider).
- [x] Build animated app layout (sidebar, top nav, breadcrumbs, page transitions).
- [x] Create shared components (PageHeader, EmptyState, ErrorState, StatCard, LoadingScreen).
- [x] Create 11 page shells with Framer Motion page transitions.
- [x] Set up React Router with nested layout routes.
- [x] Build API service layer (Axios client, typed CRUD helpers, Job service).
- [x] Verify zero TypeScript errors and successful Vite build (2415 modules).

## Phase 7: Premium Dashboard
- [x] Design dashboard data model & mock data (DashboardStats, InsightCard, TimelineEvent, QuickAction, MarketData, DashboardNotification + mock datasets).
- [x] Build AnimatedCounter component (framer-motion scroll-triggered number animation).
- [x] Build StatusBadge component (maps 16 ApplicationStatus values to Badge variants + icons).
- [x] Build WelcomeHeader (time-based greeting, date, avatar, quick search, glassmorphism).
- [x] Build StatsCards section (8 animated stat cards with trends: Total Jobs, Applied, Saved, Interviews, Offers, Rejections, Resume Score, ATS Score).
- [x] Build JobsTable (card-based premium table with search, sortable columns, salary formatting, relative time).
- [x] Build AI Insights Panel (6 insight cards with priority indicators, SVG circular scores, action buttons).
- [x] Build Applications Timeline (vertical timeline with type-colored icons, alternating layout, status badges).
- [x] Build Quick Actions grid (6 clickable action cards with lucide-react icons and colored accents).
- [x] Build Market Overview (3 chart panels: horizontal skill bars, vertical trend bars, SVG salary line chart, scroll-triggered animations).
- [x] Build Notifications Panel (notification list with type-based icons, unread indicators, mark-all-read).
- [x] Verify zero TypeScript errors and successful Vite build (2426 modules).
