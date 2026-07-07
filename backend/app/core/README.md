# backend/app/core

Core application infrastructure — configuration, security, logging, and shared utilities.

## Contents

- `settings.py` — Unified settings loader composing all domain configs
- `settings/` — Domain-specific configuration modules:
  - `app.py` — Application metadata, environment, CORS
  - `database.py` — Database connection pool and migration settings
  - `gemini.py` — LLM provider config (Gemini, Groq, Ollama)
  - `playwright.py` — Browser automation engine settings
  - `logging_settings.py` — Structured JSON logging configuration
  - `email.py` — Email monitoring for status tracking
  - `storage.py` — File storage paths and limits
  - `job_collection.py` — Job scraping and discovery parameters
  - `application.py` — Application submission and review settings
- `security.py` — API key management, encryption helpers
- `exceptions.py` — Custom exception classes and error handlers
- `constants.py` — Application-wide constants
