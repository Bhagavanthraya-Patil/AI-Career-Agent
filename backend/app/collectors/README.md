# Universal Job Collector Framework

A modular, extensible framework for collecting job listings from multiple sources. Built for the AI Career Agent.

## Architecture

```
collectors/
├── base.py          # BaseCollector abstract class
├── registry.py      # CollectorRegistry with auto-discovery
├── models.py        # Shared data models (JobData, CompanyData, etc.)
├── exceptions.py    # Exception hierarchy
├── retry.py         # Retry framework with exponential backoff
├── logging.py       # Logger protocol interface
├── config.py        # Configuration hooks into centralized settings
├── lifecycle.py     # Lifecycle documentation and stage enum
├── collectors/      # Concrete collector implementations
└── plugins/         # Plugin package (future collectors)
    ├── linkedin/
    ├── greenhouse/
    ├── lever/
    ├── workday/
    ├── ashby/
    ├── google_jobs/
    ├── wellfound/
    ├── remoteok/
    └── company_careers/
```

## Collector Lifecycle

Every collector follows this exact lifecycle, enforced by `BaseCollector.execute()`:

```
initialize() → collect() → normalize() → validate() → deduplicate() → save() → cleanup()
```

`cleanup()` is guaranteed to run even if a previous stage fails.

## How to Add a New Collector

### 1. Create the collector file

Create a new file in `collectors/collectors/` or `collectors/plugins/<name>/`:

```python
from app.collectors.base import BaseCollector
from app.collectors.models import CollectorQuery, CollectorResult, JobData
from app.collectors.registry import CollectorRegistry
from typing import Any


@CollectorRegistry.register
class MySourceCollector(BaseCollector):

    @property
    def name(self) -> str:
        return "mysource"

    @property
    def source_id(self) -> str:
        return "mysource"

    async def initialize(self) -> None:
        # Set up resources (HTTP session, browser, etc.)
        self._initialized = True

    async def collect(self, query: CollectorQuery) -> CollectorResult:
        # Execute the search, return raw results
        ...

    async def normalize(self, raw_data: Any) -> list[JobData]:
        # Convert raw source data to JobData models
        ...

    async def validate(self, jobs: list[JobData]) -> list[JobData]:
        # Filter out invalid entries
        ...

    async def deduplicate(
        self, jobs: list[JobData], existing_source_ids: list[str]
    ) -> list[JobData]:
        # Remove jobs already in the database
        ...

    async def save(self, jobs: list[JobData]) -> CollectorResult:
        # Persist jobs
        ...

    async def cleanup(self) -> None:
        # Release resources
        pass
```

### 2. Ensure discovery

Place the file in a package that `CollectorRegistry.discover()` scans:

```python
from app.collectors.registry import CollectorRegistry
CollectorRegistry.discover("app.collectors.collectors", "app.collectors.plugins")
```

Or use the `@CollectorRegistry.register` decorator.

### 3. Register the source

Add the source name to `JOB_COLLECTION_SOURCES_ENABLED` in your `.env`:

```env
JOB_COLLECTION_SOURCES_ENABLED=linkedin,indeed,mysource
```

## Required Methods

Every concrete collector must implement these abstract methods:

| Method | Input | Output | Purpose |
|---|---|---|---|
| `initialize()` | None | None | Set up resources |
| `collect(query)` | `CollectorQuery` | `CollectorResult` | Execute search |
| `normalize(raw_data)` | `Any` | `list[JobData]` | Convert to standard model |
| `validate(jobs)` | `list[JobData]` | `list[JobData]` | Filter invalid entries |
| `deduplicate(jobs, existing_ids)` | `list[JobData]`, `list[str]` | `list[JobData]` | Remove duplicates |
| `save(jobs)` | `list[JobData]` | `CollectorResult` | Persist to database |
| `cleanup()` | None | None | Release resources |

Properties:
- `name` — Human-readable collector name
- `source_id` — Unique source identifier (matches `job_sources` table)

## Expected Inputs

- `CollectorQuery` — Search parameters (keywords, locations, filters, limits)
- Configuration from `CollectorConfigProvider` (reads from `settings.job_collection`)
- `existing_source_ids` — List of known source job IDs for deduplication

## Expected Outputs

- `CollectorResult` — Complete collection result with:
  - `jobs`: List of `JobData` records
  - `stats`: `CollectionStats` (counts per lifecycle stage)
  - `errors`: List of `ErrorReport` for failed items
  - `success`: Overall success flag

## Data Models

| Model | Fields | Purpose |
|---|---|---|
| `CollectorQuery` | keywords, locations, filters, max_results | Search parameters |
| `JobData` | title, company, location, salary, metadata, description | Normalized job record |
| `CompanyData` | name, website, industry, size, location | Employer information |
| `LocationData` | city, state, country, remote_type | Location information |
| `SalaryData` | min, max, currency, interval | Compensation information |
| `JobMetadata` | source, source_job_id, job_url, posted_at | Listing metadata |
| `CollectorResult` | source, query, jobs, stats, errors | Collection run result |
| `CollectionStats` | counts per lifecycle stage | Run statistics |
| `ErrorReport` | error_type, message, field, recoverable | Error details |

## Exception Hierarchy

```
CollectorError (base)
├── AuthenticationError    # Invalid/expired credentials
├── RateLimitError         # Rate limited (includes retry_after)
├── ParsingError           # Failed to parse source data
├── ValidationError        # Data failed validation
├── StorageError           # Failed to persist data
└── NetworkError           # Network failure (includes status_code)
```

## Retry Framework

```python
from app.collectors.retry import RetryStrategy, retry

# As a decorator
@retry(max_retries=3, timeout_seconds=30.0)
async def fetch_data(url: str) -> bytes:
    ...

# Or as a strategy object
strategy = RetryStrategy(
    max_retries=3,
    base_delay_seconds=1.0,
    backoff_multiplier=2.0,
    timeout_seconds=30.0,
)
result = await strategy.execute(fetch_data, url)
```

## Configuration

All configuration flows through the centralized settings layer:
- `CollectorConfigProvider.get_global_settings()` — `JOB_COLLECTION_*` vars
- `CollectorConfigProvider.get_playwright_settings()` — `PLAYWRIGHT_*` vars
- `CollectorConfigProvider.get_storage_settings()` — `STORAGE_*` vars
- `CollectorConfigProvider.is_source_enabled(name)` — checks enabled list
