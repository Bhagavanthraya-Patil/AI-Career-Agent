# backend/app/services

Business logic layer — integrations with external systems and shared service modules.

## Contents

- `llm_gateway.py` — Unified interface for Gemini, Groq, Ollama providers
- `pdf_generator.py` — ATS-friendly PDF and DOCX generation
- `email_monitor.py` — IMAP/Gmail API integration for status detection
- `cache.py` — LLM output caching to avoid duplicate API costs
