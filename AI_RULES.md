# AI_RULES.md — Mandatory AI Coding & Collaboration Guidelines

This document establishes the binding protocols, coding rules, and collaboration standards that **all AI models** (Gemini, OpenCode, Blackbox, KiloCode, ChatGPT, etc.) must adhere to when working on the **AI Career Agent** project.

---

## 1. AI Responsibilities
* **Strict Adherence to Architecture:** AIs must implement features within the established FastAPI backend and React/Vite frontend monorepo architecture. 
* **Zero-Cost Constraint Enforcement:** Every implementation proposal must prioritize free or open-source local/cloud tiers (e.g., SQLite, Google Gemini Free Tier, local Ollama, Vercel free hosting).
* **Defensive Coding:** Anticipate network, scraping, and LLM API failures, ensuring robust fallback mechanisms exist for all workflows.
* **Integrity of Existing Logic:** Maintain existing structure, comments, and implementation patterns unless explicitly directed otherwise.

---

## 2. What AI is Allowed to Modify
* **Feature Implementations:** Logic under `backend/app/` (agents, API routes, database schemas, services) and `frontend/src/` (components, views, state stores).
* **Automation Suites:** Scraping and submission code within the `automation/` directory.
* **Test Suites:** Code inside `backend/tests/` or frontend test configurations.
* **Configuration Files:** Local setups (e.g., Pydantic settings config) that do not leak keys.
* **Project Logs/Tracks:** `TASKS.md` and `CHANGELOG.md` files representing session progress.

---

## 3. What AI Must Never Modify
* **Environment Credentials & Secrets:** Never modify or commit `.env` or configuration defaults with hardcoded API keys/passwords.
* **Core Git Internals:** Never modify `.git/` or force-push history without manual project lead approval.
* **Undocumented Architecture Refactoring:** Never modify the high-level boundaries outlined in `PROJECT.md` without explicit permission.
* **System-wide Customizations:** Do not alter the project rule matrices (e.g., `AI_RULES.md` itself) unless directed by the human supervisor.

---

## 4. Coding Standards
### Python (Backend)
* **Style:** Strict adherence to **PEP 8** style specifications.
* **Typing:** Strict typing mandatory. Use `from typing import ...` for complex types. Every function signature must define argument types and return types.
* **Concurrency:** Use `async`/`await` for all networking and DB operations.
* **Validation:** All inputs must be parsed and verified through `Pydantic` models.

### TypeScript / React (Frontend)
* **Typing:** Strict typing is enforced; the `any` keyword is disallowed.
* **Components:** Functional components using React hooks, using clean, scoped styling.
* **State:** Use Zustand hooks rather than prop drilling or complex Context API providers.

---

## 5. Naming Conventions
* **Directories:** Lowercase with hyphens (e.g., `job-collector-agent`).
* **Python Files & Variables:** Snake_case (e.g., `job_analyzer.py`, `match_score`).
* **Python Classes:** PascalCase (e.g., `ResumeTailorService`).
* **TypeScript Files:** PascalCase for UI Components (`JobDashboard.tsx`), camelCase for utility scripts/hooks (`useAuth.ts`).
* **Constants:** UPPERCASE with underscores (e.g., `GEMINI_MAX_TOKENS`).

---

## 6. Folder Ownership
* `backend/app/agents/` $\rightarrow$ **Agents Subsystem:** Contains prompt definitions, system instructions, and agent logic.
* `backend/app/api/` $\rightarrow$ **API Gateway Subsystem:** Defines endpoint routes and payload contracts.
* `backend/app/db/` $\rightarrow$ **Persistency Subsystem:** Database models, migrations, and repository patterns.
* `automation/` $\rightarrow$ **Scraping Subsystem:** Isolated Playwright automation execution pipelines.
* `frontend/` $\rightarrow$ **User Presentation Subsystem:** All client-side UI/UX resources.

---

## 7. Git Commit Rules
* Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:
  - Format: `<type>(<scope>): <short description>`
  - Permitted types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.
* Keep commits atomic: one logical change per commit.
* Never commit secrets, keys, or local `.env` setups.

---

## 8. Documentation Update Rules
* **PROJECT.md:** The single source of truth. Any database schema updates or tool-stack modifications must be documented in `PROJECT.md` immediately.
* **CHANGELOG.md:** Must be updated at the end of **every session/turn** detailing changes made under a standard version/timestamp header.
* **TASKS.md:** Must be updated before ending any session, ticking off finished items and logging active/pending items.

---

## 9. Token Optimization Strategy
* **Read Selectively:** Never request to print or read very large files (e.g., libraries, massive datasets) in full. Utilize regex or grep-searching tools to target edits.
* **Write targeted edits:** Avoid overwriting entire files for minor changes. Use selective replacement tools (like `replace_file_content` or diffs) to save model context token budget.
* **Minimize Chat Overhead:** Keep conversational responses concise, avoiding long explanations of basic code syntax.

---

## 10. Context Loading Strategy
* At the start of a session, the AI assistant must:
  1. Read the `PROJECT.md` file to understand the architecture and tech stack.
  2. Read the `AI_RULES.md` to adhere to coding rules.
  3. Inspect `TASKS.md` to locate the current objectives.
  4. Search files selectively to load context relevant only to the immediate task.

---

## 11. Model Switching Continuation Strategy
When switching between AI models or launching subagents:
* Save a state summary file or prompt instructions containing:
  - Current task being solved.
  - Files modified so far.
  - Next logical micro-steps.
  - Unresolved issues encountered.
* Subagents must be spawned with isolated, specific instructions to prevent logic collisions.

---

## 12. Refactoring Policy
* **Never rewrite working code without justification.** If refactoring is necessary, provide a clear rationale before performing the change.
* Refactoring must only be done to:
  - Remove duplicate functionality.
  - Simplify overly complex code blocks.
  - Improve algorithmic performance.
  - Implement strong typing/modular isolation.

---

## 13. Error Fixing Policy
* Trace root errors by inspecting structured backend logs or browser execution traces first.
* Fix issues by addressing root architectural flaws rather than applying "band-aid" patches (e.g., adding catch-all `except Exception: pass`).
* If a fix requires API changes, make sure to update both frontend payload interfaces and backend validation schemas synchronously.

---

## 14. Testing Policy
* **Unit Testing:** Write descriptive tests under the `tests/` directory for any logic utility, validation schema, or database router.
* **Integration Testing:** Test API gateway routes asynchronously using test client packages (e.g., FastAPI `TestClient`).
* **Automation Testing:** Ensure Playwright test scripts can run in headed mode locally to visually confirm element selectors are correct.

---

## 15. Logging Policy
* Always log agent workflow steps, prompt outputs, and API transitions.
* Use standard logger configuration:
  - `DEBUG`: Prompt templates, raw responses, scraping selectors.
  - `INFO`: Start/finish of workflows, database migrations, server events.
  - `ERROR` / `CRITICAL`: Failures of LLM API, scraper blockades, database locks.
* Logs must be clean, structured (JSON), and devoid of sensitive user info (such as raw candidate passwords/tokens).

---

## 16. Security Policy
* **Sanitize Input Data:** Never trust input from job boards or user resumes blindly. Sanitize inputs to prevent SQL injections or Prompt Injections to LLM layers.
* **Secure API Key Management:** Enforce local-only access via environment loaders. Never print API keys in terminal commands or project logs.
* **Stealth and Safety Guidelines:** Playwright agents must not make high-frequency requests that overload websites or breach target Terms of Service.

---

## 17. Prompt Writing Guidelines
For prompt configurations in `backend/app/agents/`:
* Keep system instructions separate from user variables.
* Use structured system formats (e.g., XML/JSON markdown outputs).
* Include clear operational boundaries, failure fallback instructions, and exact response JSON schemas.
* Avoid prompt clutter; write concise, instruction-dense prompts.

---

## 18. Project Memory Strategy
* System memory is managed via local JSON trackers (`data/logs/system_memory.json`).
* Record execution metadata: successful application runs, scraper selector failures, and response latency statistics.
* This log serves to help AI models self-correct prompt selectors or scraping behaviors in subsequent runs.

---

## 19. Definition of Completed Work
A task is marked completed only when:
* Code is fully functional and handles errors gracefully.
* Source code is fully typed and free of lint errors.
* Unit tests are written and passing.
* Documentation (`CHANGELOG.md`, `TASKS.md`, and any modified file headers) are updated.

---

## 20. Handoff Checklist
Before concluding a work session and passing control back to a human or another AI model, compile a summary detailing:
* [ ] **Progress:** Which tasks in `TASKS.md` were completed.
* [ ] **Code Changes:** Files modified and created.
* [ ] **Issues & Blockers:** Any API limits, site structural changes, or errors encountered.
* [ ] **Next Steps:** Actionable next items to execute in the subsequent session.
