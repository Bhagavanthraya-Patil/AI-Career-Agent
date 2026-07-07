# Apply Agent

Automates job application form submission via Playwright browser automation.

## Architecture

```
apply_agent/
├── __init__.py              # Public API exports
├── apply_agent.py           # Primary orchestrator with lifecycle
├── application_context.py   # Per-application state (FormField, UserProfile, etc.)
├── application_result.py    # Structured result model
├── application_session.py   # Playwright session lifecycle wrapper
├── cover_letter_generator.py # AI/template cover letter generation
├── exceptions.py            # Typed exception hierarchy
├── field_fillers.py         # Fill text/dropdown/checkbox/radio/date fields
├── field_mapper.py          # Map detected field labels to canonical types
├── form_detector.py         # Detect form fields via Playwright + heuristics
├── question_answerer.py     # Answer application questions via LLM/rules
├── resume_uploader.py       # PDF/DOCX file upload via file chooser
├── state_machine.py         # Finite state machine (10 states)
├── submit_handler.py        # Review/dry_run/submit modes + verification
├── validation.py            # Pre-flight checks and field validation
└── README.md                # This file
```

## Lifecycle

The `ApplyAgent.run()` method executes the following lifecycle:

1. **Navigate** — open the application URL in the browser
2. **Analyze** — detect form fields and map to canonical types
3. **Fill** — fill all mapped fields from user profile data
4. **Upload** — upload resume and cover letter documents
5. **Cover letter** — generate cover letter via ResumeTailorAgent (optional)
6. **Questions** — answer non-standard form questions via LLM/rules
7. **Submit** — one of three modes:
   - `review` — capture screenshot, no submission
   - `dry_run` — fill form, capture screenshot, no submission
   - `submit` — click submit, detect confirmation, verify
8. **Verify** — check for confirmation code after submission

## Modes

| Mode      | Description                                      |
|-----------|--------------------------------------------------|
| `review`  | Fill form, capture screenshot for human review   |
| `dry_run` | Full fill + screenshot, no actual submission     |
| `submit`  | Full lifecycle including submission +            |
verification         |

## Usage

```python
from app.agents.apply_agent import ApplyAgent, ApplyAgentInput, ApplyAgentConfig
from app.agents.apply_agent.state_machine import ApplicationState
from app.agents.llm import LLMClient
from app.collectors.models import JobData
from app.scraping.session import BrowserSession

browser = BrowserSession(config={})
llm = LLMClient.from_settings(settings)

agent = ApplyAgent(
    browser_session=browser,
    llm_client=llm,
    logger=logger,
)
agent.register_resume_tailor(resume_tailor)
agent.register_jd_analyzer(jd_analyzer)

input_data = ApplyAgentInput(
    job=job_data,
    application_url="https://example.com/apply",
    resume_path="/path/to/resume.pdf",
    config=ApplyAgentConfig(mode="review"),
)

result = await agent.run(input_data)
print(result.summary)  # "Application completed (review/dry-run mode)."
```

## State Machine

```
initialized → page_loaded → analyzed → filled → uploaded
    → reviewed → submitted → verified
    ↓
  failed / cancelled (any state)
```

Failed applications can be retried by transitioning back to `initialized`.
