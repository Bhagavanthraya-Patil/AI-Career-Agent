# backend/app/agents/tracker

Tracker Agent — monitors application lifecycle and auto-updates status in the pipeline.

## Responsibilities

- Poll email integrations (IMAP/Gmail API) for interview invites and rejection letters
- Monitor application pipeline events and detect status transitions
- Update the `Applications` table with new statuses and timestamps

## Input

Mailbox notifications / application pipeline events

## Output

Direct state updates to the `Applications` database table
