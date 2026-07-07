# Database Design — AI Career Agent

> **Target:** PostgreSQL (with SQLite fallback for local dev)
> **Status:** Design phase — no migrations or ORM models yet
> **Principles:** Normalized, SaaS-ready, audit-traced, AI-first

---

## 1. Entity-Relationship Diagram

```mermaid
erDiagram
    users ||--o| user_profiles : has
    users ||--o{ master_resumes : owns
    users ||--o{ settings : configures
    users ||--o{ workflow_executions : triggers
    users ||--o{ ai_generations : requests

    master_resumes ||--o{ resume_versions : has

    resume_versions ||--o{ ats_analyses : evaluated_by
    resume_versions ||--o{ resume_analyses : evaluated_by
    resume_versions ||--o| cover_letters : generated_for
    resume_versions }o--o| jobs : tailored_for
    resume_versions }o--o{ skills : contains
    resume_versions }o--o{ keywords : contains

    job_sources ||--o{ companies : lists
    companies ||--o{ jobs : employs
    jobs ||--o{ job_descriptions : has
    jobs ||--o{ applications : receives
    jobs }o--o{ skills : requires
    jobs }o--o{ keywords : matches

    applications ||--|| resume_versions : uses_resume
    applications ||--o| cover_letters : uses_cover
    applications ||--o{ application_status_history : tracks
    applications ||--o{ interviews : schedules

    skills }o--o{ job_sources : ""  ""

    workflow_executions ||--o{ logs : produces
```

---

## 2. Entity Dictionary

### 2.1 users

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK, default `gen_random_uuid()` |
| tenant_id | UUID | Nullable; for future multi-tenant SaaS partitioning |
| email | VARCHAR(320) | Unique, not null |
| hashed_password | VARCHAR(255) | Not null |
| is_active | BOOLEAN | Default `true` |
| is_superuser | BOOLEAN | Default `false` |
| last_login_at | TIMESTAMPTZ | Nullable |
| created_at | TIMESTAMPTZ | Not null, default `now()` |
| updated_at | TIMESTAMPTZ | Not null, auto-update |

**Purpose:** Authentication and identity root for all user-owned data.
**Relationships:** One-to-one with `user_profiles`; one-to-many with `master_resumes`, `settings`, `workflow_executions`, `ai_generations`.
**Future:** `tenant_id` enables row-level security for SaaS. Add MFA fields, OAuth provider columns.

---

### 2.2 user_profiles

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | FK → users.id, unique |
| full_name | VARCHAR(255) | |
| phone | VARCHAR(50) | Nullable; encrypted at rest |
| location | VARCHAR(255) | Nullable |
| headline | VARCHAR(255) | Professional headline |
| summary | TEXT | Career objective / summary |
| work_history | JSONB | Array of `{company, title, start_date, end_date, description}` |
| education | JSONB | Array of `{institution, degree, field, start_date, end_date}` |
| projects | JSONB | Array of `{name, description, technologies, url}` |
| certifications | JSONB | Array of `{name, issuer, date, url}` |
| social_links | JSONB | `{linkedin, github, portfolio, twitter}` |
| preferred_roles | TEXT[] | Array of job title preferences |
| preferred_locations | TEXT[] | Array of location preferences |
| salary_expectation_min | INTEGER | Nullable |
| salary_expectation_max | INTEGER | Nullable |
| is_actively_looking | BOOLEAN | Default `true` |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

**Purpose:** Extended user profile with structured career data used by agents for tailoring.
**Relationships:** One-to-one with `users`.
**Future:** Add `resume_parse_source` (LinkedIn import JSON), vector embedding column for semantic search.

---

### 2.3 master_resumes

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | FK → users.id |
| title | VARCHAR(255) | e.g., "General Resume", "Software Engineer Focus" |
| is_default | BOOLEAN | Default `false`; only one default per user |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

**Purpose:** Logical grouping container for resume versions. A user can have multiple master resumes (e.g., one per career focus).
**Relationships:** One-to-many with `resume_versions`; many-to-one with `users`.
**Future:** Add `industry` field for resume specialization.

---

### 2.4 resume_versions

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| master_resume_id | UUID | FK → master_resumes.id |
| job_id | UUID | FK → jobs.id, nullable; null means "base/untailored" |
| version_number | INTEGER | Auto-increment within a master resume |
| title | VARCHAR(255) | Display name, e.g., "Tailored for Acme Corp" |
| content_markdown | TEXT | Full resume content in markdown |
| content_json | JSONB | Structured resume data (sections, bullets) |
| file_path_pdf | VARCHAR(500) | Path to generated PDF |
| file_path_docx | VARCHAR(500) | Path to generated DOCX |
| is_active | BOOLEAN | Default `true`; soft-delete support |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

**Purpose:** A specific version of a resume, optionally tailored for a specific job.
**Relationships:** Many-to-one with `master_resumes`; many-to-one with `jobs` (optional); one-to-many with `ats_analyses`, `resume_analyses`; one-to-one with `cover_letters` (optional); many-to-many with `skills`, `keywords`.
**Future:** Add `ai_generation_id` FK to trace which AI call produced this version.

---

### 2.5 job_sources

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| name | VARCHAR(100) | e.g., "LinkedIn", "Indeed", "Greenhouse" |
| base_url | VARCHAR(500) | Platform base URL |
| is_active | BOOLEAN | Default `true` |
| scraper_config | JSONB | Selectors, rate limits, headers |
| created_at | TIMESTAMPTZ | |

**Purpose:** Registry of job board platforms that the Job Collector Agent scrapes.
**Relationships:** Referenced by jobs, but sources are independent of companies.
**Future:** Add API key fields for platforms that offer official APIs.

---

### 2.6 companies

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| name | VARCHAR(255) | Not null |
| website | VARCHAR(500) | Nullable |
| industry | VARCHAR(255) | Nullable |
| size | VARCHAR(50) | Nullable, e.g., "51-200 employees" |
| location | VARCHAR(255) | HQ location |
| description | TEXT | Nullable |
| logo_url | VARCHAR(500) | Nullable |
| created_at | TIMESTAMPTZ | |

**Purpose:** Normalized company catalog to avoid duplicate employers across job listings.
**Relationships:** One-to-many with `jobs`.
**Future:** Add `crunchbase_id`, `linkedin_url` for enrichment.

---

### 2.7 jobs

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| company_id | UUID | FK → companies.id |
| source_id | UUID | FK → job_sources.id |
| source_job_id | VARCHAR(255) | Platform-specific job ID for dedup |
| title | VARCHAR(255) | |
| location | VARCHAR(255) | |
| remote_type | VARCHAR(50) | "remote", "hybrid", "onsite" |
| salary_min | INTEGER | Nullable |
| salary_max | INTEGER | Nullable |
| salary_currency | VARCHAR(3) | Default "USD" |
| employment_type | VARCHAR(50) | "full-time", "part-time", "contract" |
| experience_level | VARCHAR(50) | "entry", "mid", "senior", "lead" |
| job_url | VARCHAR(1000) | Direct link to posting |
| apply_url | VARCHAR(1000) | Direct application link |
| status | VARCHAR(50) | `discovered`, `analyzed`, `applied`, `closed`, `filled` |
| is_active | BOOLEAN | Default `true` |
| posted_at | TIMESTAMPTZ | Nullable |
| scraped_at | TIMESTAMPTZ | |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

**Purpose:** Core job listing record — the central entity that all agents operate on.
**Relationships:** Many-to-one with `companies`, `job_sources`; one-to-many with `applications`, `job_descriptions`; many-to-many with `skills`, `keywords`.
**Future:** Add `vector_embedding` column for semantic similarity search.

---

### 2.8 job_descriptions

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| job_id | UUID | FK → jobs.id |
| version | INTEGER | Tracks re-scrapes or re-parses |
| raw_html | TEXT | Original scraped HTML |
| raw_text | TEXT | Extracted plain text |
| parsed_json | JSONB | Structured output from JD Analyzer |
| is_current | BOOLEAN | Default `true` |
| created_at | TIMESTAMPTZ | |

**Purpose:** Stores the evolution of a job description (platforms often update postings). Raw + parsed separation enables re-analysis without re-scraping.
**Relationships:** Many-to-one with `jobs`.
**Future:** Add diff tracking between versions.

---

### 2.9 skills

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| name | VARCHAR(255) | Unique, normalized (e.g., "Python") |
| category | VARCHAR(100) | "language", "framework", "tool", "soft_skill", "domain" |
| description | TEXT | Nullable |
| aliases | TEXT[] | Alternative names (e.g., ["JS", "ES6"]) |
| created_at | TIMESTAMPTZ | |

**Purpose:** Normalized skill catalog used across jobs, resumes, and profiles. Avoids duplicate skill entries.
**Relationships:** Many-to-many with `jobs` (via `job_skills`), `resume_versions` (via `resume_version_skills`).

**Join Table: job_skills**

| Field | Type |
|---|---|
| job_id | UUID | FK → jobs.id |
| skill_id | UUID | FK → skills.id |
| importance | VARCHAR(20) | "required", "preferred", "bonus" |

**Join Table: resume_version_skills**

| Field | Type |
|---|---|
| resume_version_id | UUID | FK → resume_versions.id |
| skill_id | UUID | FK → skills.id |
| proficiency | VARCHAR(20) | "beginner", "intermediate", "advanced", "expert" |

---

### 2.10 keywords

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| word | VARCHAR(255) | Unique, lowercase, trimmed |
| created_at | TIMESTAMPTZ | |

**Purpose:** Normalized keyword catalog extracted from job descriptions for matching and density analysis.
**Relationships:** Many-to-many with `jobs` (via `job_keywords`), `resume_versions` (via `resume_version_keywords`).

**Join Table: job_keywords**

| Field | Type |
|---|---|
| job_id | UUID | FK → jobs.id |
| keyword_id | UUID | FK → keywords.id |
| frequency | INTEGER | Count of occurrences in JD |

**Join Table: resume_version_keywords**

| Field | Type |
|---|---|
| resume_version_id | UUID | FK → resume_versions.id |
| keyword_id | UUID | FK → keywords.id |
| frequency | INTEGER | Count of occurrences in resume |

---

### 2.11 ats_analyses

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| resume_version_id | UUID | FK → resume_versions.id |
| match_score | DECIMAL(5,2) | 0.00–100.00 |
| keyword_coverage | DECIMAL(5,2) | Percentage of JD keywords present |
| section_scores | JSONB | Per-section breakdown `{summary: 85, experience: 72, skills: 90}` |
| missing_keywords | TEXT[] | Critical keywords absent from resume |
| suggestions | JSONB | Array of actionable `{section, issue, suggestion}` |
| raw_llm_response | JSONB | Complete LLM output for audit |
| ai_generation_id | UUID | FK → ai_generations.id, nullable |
| created_at | TIMESTAMPTZ | |

**Purpose:** Result of the ATS Analyzer Agent — scores resume-JD compatibility.
**Relationships:** Many-to-one with `resume_versions`; many-to-one with `ai_generations`.

---

### 2.12 resume_analyses

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| resume_version_id | UUID | FK → resume_versions.id |
| overall_score | DECIMAL(5,2) | 0.00–100.00 |
| readability_score | DECIMAL(5,2) | |
| ats_compatibility_score | DECIMAL(5,2) | |
| length_analysis | JSONB | `{total_words, sections, recommended_changes}` |
| grammar_issues | JSONB | Array of detected issues |
| formatting_suggestions | JSONB | |
| raw_llm_response | JSONB | |
| ai_generation_id | UUID | FK → ai_generations.id, nullable |
| created_at | TIMESTAMPTZ | |

**Purpose:** Quality analysis of a resume independent of any specific job. Used for general improvement suggestions.
**Relationships:** Many-to-one with `resume_versions`; many-to-one with `ai_generations`.

---

### 2.13 cover_letters

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| resume_version_id | UUID | FK → resume_versions.id, unique |
| job_id | UUID | FK → jobs.id |
| content_markdown | TEXT | Full letter in markdown |
| file_path_pdf | VARCHAR(500) | |
| file_path_docx | VARCHAR(500) | |
| tone | VARCHAR(50) | "professional", "enthusiastic", "formal" |
| word_count | INTEGER | |
| raw_llm_response | JSONB | |
| ai_generation_id | UUID | FK → ai_generations.id, nullable |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

**Purpose:** AI-generated cover letter tailored to a specific job and resume version.
**Relationships:** One-to-one with `resume_versions`; many-to-one with `jobs`, `ai_generations`.

---

### 2.14 applications

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | FK → users.id |
| job_id | UUID | FK → jobs.id |
| resume_version_id | UUID | FK → resume_versions.id |
| cover_letter_id | UUID | FK → cover_letters.id, nullable |
| status | VARCHAR(50) | `discovered`, `analyzed`, `tailored`, `pending_review`, `submitted`, `interviewing`, `offered`, `rejected`, `withdrawn` |
| applied_date | DATE | Nullable |
| submission_confirmation | VARCHAR(500) | Confirmation code or screenshot path |
| notes | TEXT | User notes |
| rating | INTEGER | User rating 1-5, nullable |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

**Purpose:** Tracks the lifecycle of a user's application to a specific job.
**Relationships:** Many-to-one with `users`, `jobs`, `resume_versions`; one-to-one with `cover_letters` (optional); one-to-many with `application_status_history`, `interviews`.
**Future:** Add `tenant_id` for SaaS. Add `source` field ("auto", "manual", "import").

---

### 2.15 application_status_history

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| application_id | UUID | FK → applications.id |
| from_status | VARCHAR(50) | Nullable for initial state |
| to_status | VARCHAR(50) | Not null |
| changed_by | VARCHAR(50) | "system", "user", "agent:tacker", "agent:apply" |
| reason | TEXT | Nullable context/note |
| created_at | TIMESTAMPTZ | |

**Purpose:** Immutable audit log of every status transition for an application. Enables timeline visualization and debugging.
**Relationships:** Many-to-one with `applications`.
**Future:** Add `metadata` JSONB for additional context (e.g., email snippet for rejection).

---

### 2.16 interviews

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| application_id | UUID | FK → applications.id |
| round | INTEGER | 1 = first, 2 = second, etc. |
| interview_type | VARCHAR(50) | "phone", "video", "onsite", "technical", "behavioral" |
| scheduled_at | TIMESTAMPTZ | |
| duration_minutes | INTEGER | Nullable |
| status | VARCHAR(50) | `scheduled`, `completed`, `cancelled`, `rescheduled` |
| notes | TEXT | User notes after interview |
| follow_up_action | TEXT | Next steps |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

**Purpose:** Tracks interview events for each application.
**Relationships:** Many-to-one with `applications`.
**Future:** Add AI-generated prep questions, feedback recording, calendar integration.

---

### 2.17 ai_generations

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | FK → users.id |
| agent_name | VARCHAR(100) | e.g., "jd_analyzer", "resume_tailor", "cover_letter" |
| model_used | VARCHAR(100) | "gemini-2.0-flash", "llama-3.1-8b", etc. |
| prompt_template | TEXT | Template identifier or hash |
| prompt_input | JSONB | Full input sent to the model |
| raw_output | JSONB | Full response from the model |
| tokens_input | INTEGER | |
| tokens_output | INTEGER | |
| latency_ms | INTEGER | |
| success | BOOLEAN | |
| error_message | TEXT | Nullable |
| created_at | TIMESTAMPTZ | |

**Purpose:** Audit log of every AI model invocation. Enables cost tracking, debugging, and prompt iteration.
**Relationships:** Many-to-one with `users`; referenced by `ats_analyses`, `resume_analyses`, `cover_letters`.
**Future:** Add cost tracking (per-model pricing), feedback rating for output quality.

---

### 2.18 workflow_executions

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | FK → users.id |
| workflow_name | VARCHAR(100) | e.g., "discover_and_analyze", "tailor_and_apply" |
| trigger | VARCHAR(50) | "manual", "scheduled", "event" |
| status | VARCHAR(50) | `pending`, `running`, `completed`, `failed`, `cancelled` |
| input_params | JSONB | Initial parameters |
| result_summary | JSONB | High-level results |
| started_at | TIMESTAMPTZ | |
| completed_at | TIMESTAMPTZ | Nullable |
| created_at | TIMESTAMPTZ | |

**Purpose:** Orchestration tracking for multi-agent workflows. Enables monitoring and retry logic.
**Relationships:** Many-to-one with `users`; one-to-many with `logs`.
**Future:** Add DAG/task graph representation, parallel branch tracking.

---

### 2.19 settings

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | FK → users.id, nullable (null = global default) |
| key | VARCHAR(255) | Dot-notation, e.g., `application.max_daily`, `scraper.rate_limit_ms` |
| value | JSONB | Flexible value storage |
| description | TEXT | Human-readable explanation |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

**Purpose:** Key-value configuration store for user preferences and system defaults. Supports per-user overrides of global defaults.
**Relationships:** Many-to-one with `users` (nullable).
**Future:** Add `setting_group` for UI categorization, validation schema.

---

### 2.20 logs

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| workflow_execution_id | UUID | FK → workflow_executions.id, nullable |
| level | VARCHAR(20) | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| logger | VARCHAR(100) | Module/class name |
| message | TEXT | |
| metadata | JSONB | Structured context (agent name, job ID, etc.) |
| created_at | TIMESTAMPTZ | |

**Purpose:** Structured application logs for debugging, monitoring, and audit. Lighter than `ai_generations` — captures operational telemetry.
**Relationships:** Many-to-one with `workflow_executions` (optional).
**Future:** Add TTL-based partitioning for log rotation.

---

## 3. Indexing Strategy

| Table | Index | Type | Purpose |
|---|---|---|---|
| users | `uq_users_email` | UNIQUE | Login lookup |
| users | `idx_users_tenant_id` | BTREE | SaaS tenant isolation |
| jobs | `idx_jobs_company_id` | BTREE | Company job listing queries |
| jobs | `idx_jobs_status` | BTREE | Filter by pipeline status |
| jobs | `idx_jobs_scraped_at` | BTREE | Time-based job discovery |
| jobs | `uq_jobs_source_job_id` | UNIQUE | Dedup across platforms |
| applications | `idx_applications_user_id` | BTREE | User's application dashboard |
| applications | `idx_applications_status` | BTREE | Pipeline filter queries |
| resume_versions | `idx_resume_versions_master` | BTREE | Resume history lookup |
| application_status_history | `idx_hist_application_id` | BTREE | Timeline queries |
| ai_generations | `idx_ai_gen_user_id` | BTREE | User cost/usage dashboard |
| ai_generations | `idx_ai_gen_agent_name` | BTREE | Per-agent cost analysis |
| logs | `idx_logs_workflow` | BTREE | Workflow trace debugging |
| logs | `idx_logs_created_at` | BTREE | Time-range queries |

---

## 4. PostgreSQL-Specific Design Decisions

| Decision | Rationale |
|---|---|
| **UUID PKs** | Avoids sequential ID enumeration, supports distributed/offline generation, aligns with SaaS tenant isolation |
| **TIMESTAMPTZ** | Timezone-aware timestamps prevent DST and multi-region issues |
| **JSONB** | Flexible schema for semi-structured data (work history, parsed JD, LLM outputs) without join explosion |
| **ENUMs via VARCHAR** | Keeps SQLite compatibility for local dev; application-level validation in Pydantic enforces correctness |
| **TEXT[] arrays** | Native PostgreSQL array type for simple tag-like data (preferred_roles, missing_keywords) |
| **Join tables** | Proper many-to-many relationships for skills/keywords enable complex queries (e.g., "jobs requiring Python that I haven't applied to") |
| **Separate status_history** | Immutable audit trail vs mutable current status — enables timeline UIs and debugging |

---

## 5. Local Dev vs. Production

| Aspect | Local (SQLite) | Production (PostgreSQL) |
|---|---|---|
| PK type | UUID (text stored) | UUID (native) |
| JSON | JSON text | JSONB |
| Arrays | Text-as-list | TEXT[] |
| Timestamps | ISO text | TIMESTAMPTZ |
| Enums | VARCHAR check | VARCHAR (or native ENUM) |
| Migrations | Alembic with SQLite dialect | Alembic with PostgreSQL dialect |

SQLAlchemy abstract the differences; Alembic handles dialect-specific DDL.

---

## 6. Entity Count Summary

| Entity | Records (est. per user/month) |
|---|---|
| users | 1 |
| user_profiles | 1 |
| master_resumes | 1–3 |
| resume_versions | 20–100 |
| job_sources | 5–10 (global) |
| companies | 50–500 |
| jobs | 100–1000 |
| job_descriptions | 100–1000 |
| skills | 500–5000 (global catalog) |
| keywords | 1000–10000 (global catalog) |
| ats_analyses | 20–100 |
| resume_analyses | 20–100 |
| cover_letters | 20–100 |
| applications | 50–200 |
| application_status_history | 200–1000 |
| interviews | 10–100 |
| ai_generations | 200–2000 |
| workflow_executions | 50–500 |
| settings | 10–50 |
| logs | 1000–10000 |
