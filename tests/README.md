# tests

Top-level test suites for the AI Career Agent.

## Structure

- `unit/` — Unit tests for individual modules and utilities
- `integration/` — Integration tests for cross-module workflows and agent orchestration

## Testing Principles

- Every service and utility must have corresponding unit tests
- Integration tests cover end-to-end agent workflows
- Mock external APIs (LLM, scraping targets) to ensure deterministic tests
