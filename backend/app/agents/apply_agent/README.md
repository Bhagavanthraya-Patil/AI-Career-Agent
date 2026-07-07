# backend/app/agents/apply_agent

Apply Agent — automates job application form submission via headless/headed browser.

## Responsibilities

- Launch Playwright browser sessions to job application portals
- Auto-fill personal details, work history, and questionnaire answers
- Present pre-filled form screenshot for user review before submission
- Handle non-standard questions by pausing for user input

## Input

Job URL, user profile credentials, tailored resume and cover letter

## Output

Screenshot of pre-filled form + final submission confirmation
