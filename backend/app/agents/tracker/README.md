# Application Tracker Agent

Records, updates, and manages the lifecycle of job applications.

## Architecture

```
tracker/
├── __init__.py              # Public API exports
├── tracker_agent.py         # Primary orchestrator with lifecycle
├── application_tracker.py   # Core tracking service
├── status_manager.py        # Status transition validation
├── history_manager.py       # Immutable event history recording
├── metrics.py               # Aggregate metrics computation
├── timeline.py              # Chronological timeline building
├── tracker_repository.py    # SQLAlchemy repository (Application + History)
├── tracker_models.py        # Data models (dataclass-based)
├── tracker_events.py        # Event definitions for lifecycle
├── exceptions.py            # Typed exception hierarchy
└── README.md                # This file
```

## Status Lifecycle

```
draft -> ready -> applied -> submitted -> viewed -> assessment
    |         |          |          |          |
    v         v          v          v          v
cancelled  withdrawn    failed    failed   rejected
    |
    v
assessment -> interview -> technical_interview -> hr_interview -> offer -> accepted
    |              |               |               |              |
    v              v               v               v              v
 rejected     rejected        rejected         rejected      rejected/withdrawn/expired
```

All statuses can transition to `withdrawn`, `cancelled`, or `expired`.

## Lifecycle

The `TrackerAgent` lifecycle:

1. **initialize()** — Verify DB connection, create ApplicationTracker
2. **track_application()** — Create a new application record for a job
3. **update_status()** — Change status with validated transition + history
4. **record_event()** — Record an external status change event
5. **record_apply_result()** — Record Apply Agent result
6. **get_history()** — Get immutable status change history
7. **get_timeline()** — Get chronological application timeline
8. **get_metrics()** — Compute aggregate metrics
9. **cleanup()** — Deactivate terminal-status applications

## Usage

```python
from app.agents.tracker import TrackerAgent, ApplyAgentIntegration

async with get_session() as session:
    agent = TrackerAgent(session=session, logger=logger)
    await agent.initialize()

    # Track a new application
    app = await agent.track_application(
        job_id="some-job-uuid",
        apply_url="https://example.com/apply",
        resume_version="v1",
    )

    # Update status
    app = await agent.update_status(
        app.application_id,
        "applied",
        changed_by="user",
        reason="Manually applied",
    )

    # Record Apply Agent result
    result = ApplyAgentIntegration(
        success=True,
        final_state="verified",
        confirmation_code="CONF-123",
        screenshot_path="/screenshots/conf.png",
        errors=[],
        duration_seconds=45.2,
        state_history=[],
    )
    await agent.record_apply_result(app.application_id, result)

    # Get metrics
    metrics = await agent.get_metrics()
    print(metrics.success_rate)

    # Get timeline
    timeline = await agent.get_timeline(app.application_id)
    for entry in timeline.entries:
        print(entry.timestamp, entry.title)

    await agent.cleanup()
```

## Extension Guide

### Adding a new status

1. Add the new status string to `VALID_STATUSES` in `status_manager.py`.
2. Add valid transitions to `VALID_TRANSITIONS` dict.
3. Add to appropriate category sets (SUCCESS_STATUSES, etc.) if needed.
4. Optionally add patterns to `field_mapper.py` for auto-classification.

### Adding a new metric

1. Add field to `TrackerMetrics` dataclass in `tracker_models.py`.
2. Compute the value in `Metrics.compute()`.
3. Add to `TrackerMetrics.to_dict()`.

### Adding a new event type

1. Create a new `@dataclass` in `tracker_events.py` extending `TrackerEvent`.
2. Create the `TimelineEntry` in `Timeline.build()` if it should appear in timelines.

### Integration with Apply Agent

The `ApplyAgentIntegration` dataclass captures the Apply Agent's output.
The `TrackerAgent.record_apply_result()` method stores the result and
automatically updates the application status to "submitted" or "failed".

## Configuration

See `TrackerConfig` in `tracker_models.py`:

| Field | Default | Description |
|-------|---------|-------------|
| `status_after_apply` | "applied" | Default status when marking as applied |
| `record_history` | True | Whether to record status history |
| `deduplicate_by_job` | True | Prevent tracking same job twice |
| `auto_cleanup` | True | Clean up on lifecycle cleanup |
| `max_history_entries` | 1000 | Maximum history entries |
