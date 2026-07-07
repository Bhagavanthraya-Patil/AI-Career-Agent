# Parsing Rules Engine

Reusable, field-level parsing rules that normalize raw job listing
fields into structured data models. Every collector source uses this
engine so parsing logic is written once, tested once, and shared
everywhere.

---

## Architecture

```
app/parsers/
  base.py               # BaseParser abstract class (Generic[T])
  config.py             # ParserConfigProvider — reads from ParsingSettings
  models.py             # ParsedEmploymentType, ParsedExperience, etc.
  salary_parser.py      # SalaryParser -> SalaryData (collectors.models)
  location_parser.py    # LocationParser -> LocationData (collectors.models)
  employment_type_parser.py  # EmploymentTypeParser -> ParsedEmploymentType
  experience_parser.py  # ExperienceParser -> ParsedExperience
  company_parser.py     # CompanyParser -> ParsedCompany
  title_parser.py       # TitleParser -> ParsedTitle
  metadata_parser.py    # MetadataParser -> ParsedMetadata
  registry.py           # ParserRegistry — registration + lookup
  __init__.py           # Auto-registers all built-in parsers
```

### Key Design Decisions

1. **Stateless Parsers** — Parsers hold no mutable state. All behavior
   is driven by injected configuration.

2. **Shared Data Models** — Reuses `SalaryData` and `LocationData`
   from `app.collectors.models` so collectors and parsers speak the
   same schema.

3. **Plugin Registry** — `ParserRegistry` mirrors `CollectorRegistry`.
   New parsers register via `ParserRegistry.register()` and are
   automatically discoverable.

4. **Centralized Configuration** — All synonyms, ranges, keywords,
   and format strings live in `app.core.settings.parsing.ParsingSettings`
   (env vars with `PARSING_` prefix). No values are hardcoded.

5. **Logger Agnostic** — Parsers accept any object implementing
   `CollectorLoggerProtocol` for structured logging.

---

## Parser Responsibilities

| Parser | Input | Output | Example |
|--------|-------|--------|---------|
| `SalaryParser` | str | `SalaryData` | `"$120k"`→ min=120000, USD, yearly |
| `LocationParser` | str | `LocationData` | `"Remote (India)"`→ remote, IN |
| `EmploymentTypeParser` | str | `ParsedEmploymentType` | `"FTE"`→ full-time |
| `ExperienceParser` | str | `ParsedExperience` | `"5+ years"`→ senior, 5yr |
| `CompanyParser` | str | `ParsedCompany` | `"Eng > Backend"`→ dept=Engineering |
| `TitleParser` | str | `ParsedTitle` | `"Senior Engineer"`→ Engineer, senior |
| `MetadataParser` | dict | `ParsedMetadata` | Full dict with IDs, dates, tags |

---

## Normalization Rules

### Salary
- **INR**: `₹8 LPA` → min=800000 INR yearly, `₹12-18 LPA` → 1200000-1800000
- **USD**: `$120k` → 120000, `$80k-$120k` → range, `$50/hr` → hourly
- **EUR/GBP**: `€70k`, `£50k` with correct currency codes
- **Textual**: `"Competitive"`, `"Negotiable"`, `"Unknown"` → None
- **Interval detection**: `/hr` → hourly, `/mo` → monthly, defaults to yearly

### Location
- **Remote**: Exact match or suffix `(Remote)` → remote_type=remote
- **Remote (Country)**: `Remote (India)` → remote + country=India
- **Hybrid**: `Hybrid - NY` → hybrid + city=NY
- **Onsite**: `San Francisco, CA` → city, state detected
- **US States**: 2-letter codes matched against standard abbreviations

### Employment Type
- Synonym map: `fte`→full-time, `c2h`→contract, `coop`→internship, etc.
- All configurable via `employment_synonyms` in settings

### Experience
- **Fresher** patterns: `fresher`, `0 years`, `new grad`, `entry level`
- **Year ranges**: `3-5 years` → min=3, max=5, level=mid
- **Min years**: `5+ years` → min=5, level=senior
- **Level keywords**: `senior`→senior, `principal`→principal, etc.
- Year-to-level mapping configurable via `experience_year_ranges`

### Company Hierarchy
- Separators: `>`, `/`, `|`, `-`, `::`, `»`
- Classification: first part = company name; subsequent parts mapped
  to department, team, or business unit using keyword lists

### Title
- Seniority prefix detection: `Senior Engineer` → Engineer + senior
- Role categorization: maps to engineering, product, design, etc.
- Stopword stripping: `II`, `III`, ` - ` removed from normalized form

### Metadata
- Job ID extraction from URLs via 7 regex patterns
- Reference/requisition ID from explicit fields
- Date parsing via 14 configurable format strings
- Language detection via regex against 30+ languages
- Custom fields: all keys outside known schema go to `custom` dict

---

## Extension Pattern

Adding a new parser for a custom field type:

```python
from app.parsers.base import BaseParser
from app.parsers.registry import ParserRegistry

class CustomFieldParser(BaseParser[dict]):
    name = "custom_field"

    def parse(self, raw, **context):
        # your normalization logic
        return {"normalized": raw.strip().lower()}

ParserRegistry.register(CustomFieldParser)
```

No other file needs to change. The parser is immediately available:
```python
parser = ParserRegistry.get_or_create("custom_field")
result = parser.parse("Some Raw Value")
```

To override configuration at runtime:
```python
parser = ParserRegistry.get("salary", config={
    "default_currency": "EUR",
    "default_interval": "monthly",
})
```

---

## Integration with Collectors

Collectors use parsers during their ``normalize()`` stage:

```python
from app.parsers import ParserRegistry

class MyCollector(BaseCollector):
    async def normalize(self, raw_job: dict) -> JobData:
        salary_parser = ParserRegistry.get_or_create("salary")
        loc_parser = ParserRegistry.get_or_create("location")

        return JobData(
            title=raw_job.get("title", ""),
            salary=salary_parser.parse(raw_job.get("salary")),
            location=loc_parser.parse(raw_job.get("location")),
            ...
        )
```

The ParserRegistry caches instances internally so parsers are created
once and reused across all calls, keeping overhead minimal.

---

## Commands

```bash
# Run all tests
pytest

# Run only parser tests
pytest tests/test_parsers.py -v

# Run a specific parser test class
pytest tests/test_parsers.py::TestSalaryParser -v

# Run with coverage
pytest --cov=app.parsers tests/test_parsers.py -v
```
