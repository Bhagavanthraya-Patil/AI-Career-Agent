from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import pytest_asyncio

from app.collectors.models import CollectorQuery
from app.collectors.plugins.ashby.collector import (
    ASHBY_API_BASE,
    AshbyCollector,
)


@pytest_asyncio.fixture(scope="module", autouse=True)
async def auto_create_tables():
    from app.db.session import create_tables

    await create_tables()


@pytest.fixture
def config() -> dict[str, Any]:
    return {
        "max_retries": 1,
        "retry_backoff_factor": 1.0,
        "max_pages_per_source": 3,
    }


@pytest.fixture
def collector(config: dict[str, Any]) -> AshbyCollector:
    return AshbyCollector(config)


@pytest.fixture
def query() -> CollectorQuery:
    return CollectorQuery(
        keywords=["software engineer"],
        locations=["Remote"],
        additional_filters={"board_token": "exampleco"},
    )


def _mock_response(
    status_code: int = 200,
    json_data: Any = None,
    headers: dict[str, str] | None = None,
) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.headers = headers or {}
    if json_data is not None:
        resp.json = MagicMock(return_value=json_data)
    else:
        resp.json = MagicMock(side_effect=ValueError("No JSON"))
    return resp


def _sample_posting(
    posting_id: str = "abc123",
    title: str = "Software Engineer",
    location: str = "San Francisco, CA",
    department: str = "Engineering",
    job_type: str = "Full-Time",
    remote: bool = False,
    include_compensation: bool = False,
    listed: bool = True,
) -> dict[str, Any]:
    posting: dict[str, Any] = {
        "id": posting_id,
        "type": job_type,
        "title": title,
        "description": f"<div>Description for {title}</div>",
        "locations": [location],
        "department": department,
        "companyName": "ExampleCo",
        "postingUrl": f"https://jobs.ashbyhq.com/exampleco/{posting_id}",
        "applyUrl": f"https://jobs.ashbyhq.com/exampleco/{posting_id}/application",
        "publishedAt": "2026-01-15T00:00:00.000Z",
        "isListed": listed,
    }
    if remote:
        posting["locations"] = ["Remote, United States"]
    if include_compensation:
        posting["compensationSummary"] = "$100,000 - $150,000 USD"
    return posting


class TestAshbyCollector:
    """Test suite for AshbyCollector."""

    async def _patch_client(
        self,
        collector: AshbyCollector,
        mock_responses: list[MagicMock],
    ) -> None:
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock()
        mock_client.get.side_effect = mock_responses
        mock_client.aclose = AsyncMock()
        collector._client = mock_client
        collector._initialized = True

    @patch("app.collectors.plugins.ashby.collector.RetryStrategy.execute")
    async def test_successful_collection(
        self,
        mock_retry_execute: AsyncMock,
        collector: AshbyCollector,
        query: CollectorQuery,
    ) -> None:
        job1 = _sample_posting("abc123", title="Software Engineer")
        job2 = _sample_posting("def456", title="Senior Engineer")

        mock_retry_execute.return_value = _mock_response(
            json_data={"jobs": [job1, job2]},
        )

        result = await collector.execute(query)

        assert result.success is True
        assert len(result.jobs) == 2
        assert result.stats.total_discovered == 2
        assert result.stats.total_saved == 2
        assert result.stats.total_normalized == 2
        assert result.stats.total_valid == 2
        assert result.stats.total_failed == 0

        assert result.jobs[0].title == "Software Engineer"
        assert result.jobs[0].metadata.source_job_id == "abc123"
        assert (
            result.jobs[0].metadata.job_url
            == "https://jobs.ashbyhq.com/exampleco/abc123"
        )
        assert result.jobs[0].company.name == "ExampleCo"
        assert result.jobs[0].location.city == "San Francisco"
        assert result.jobs[0].location.state == "CA"
        assert result.jobs[0].location.remote_type == "onsite"
        assert result.jobs[0].employment_type == "full-time"
        assert (
            "Description for Software Engineer" in result.jobs[0].description_raw
        )
        assert result.jobs[0].metadata.posted_at == datetime(
            2026, 1, 15, 0, 0, 0, tzinfo=timezone.utc
        )
        assert result.jobs[0].skills == ["Engineering"]

    @patch("app.collectors.plugins.ashby.collector.RetryStrategy.execute")
    async def test_empty_response(
        self,
        mock_retry_execute: AsyncMock,
        collector: AshbyCollector,
        query: CollectorQuery,
    ) -> None:
        mock_retry_execute.return_value = _mock_response(json_data={"jobs": []})

        result = await collector.execute(query)

        assert result.success is True
        assert len(result.jobs) == 0
        assert result.stats.total_discovered == 0
        assert result.stats.total_saved == 0

    @patch("app.collectors.plugins.ashby.collector.RetryStrategy.execute")
    async def test_max_results_respected(
        self,
        mock_retry_execute: AsyncMock,
        collector: AshbyCollector,
    ) -> None:
        query = CollectorQuery(
            max_results=1,
            additional_filters={"board_token": "exampleco"},
        )
        jobs_data = [
            _sample_posting("id1", title="Job 1"),
            _sample_posting("id2", title="Job 2"),
        ]

        mock_retry_execute.return_value = _mock_response(json_data={"jobs": jobs_data})

        result = await collector.execute(query)

        assert result.success is True
        assert len(result.jobs) == 1
        assert result.jobs[0].metadata.source_job_id == "id1"

    @patch("app.collectors.plugins.ashby.collector.RetryStrategy.execute")
    async def test_network_error_handling(
        self,
        mock_retry_execute: AsyncMock,
        collector: AshbyCollector,
        query: CollectorQuery,
    ) -> None:
        from app.collectors.exceptions import NetworkError

        mock_retry_execute.side_effect = NetworkError(
            "Connection failed",
            source="ashby",
        )

        result = await collector.execute(query)

        assert result.success is False
        assert len(result.jobs) == 0
        assert len(result.errors) >= 1
        assert any("NetworkError" in e.error_type for e in result.errors)

    @patch("app.collectors.plugins.ashby.collector.RetryStrategy.execute")
    async def test_retry_on_rate_limit(
        self,
        mock_retry_execute: AsyncMock,
        collector: AshbyCollector,
        query: CollectorQuery,
    ) -> None:
        from app.collectors.exceptions import RateLimitError

        mock_retry_execute.side_effect = RateLimitError(
            "Rate limited",
            retry_after=1.0,
            source="ashby",
        )

        result = await collector.execute(query)

        assert result.success is False
        assert len(result.errors) >= 1
        assert any("RateLimitError" in e.error_type for e in result.errors)

    @patch("app.collectors.plugins.ashby.collector.RetryStrategy.execute")
    async def test_invalid_json_response(
        self,
        mock_retry_execute: AsyncMock,
        collector: AshbyCollector,
        query: CollectorQuery,
    ) -> None:
        from app.collectors.exceptions import ParsingError

        mock_retry_execute.side_effect = ParsingError(
            "Invalid JSON from Ashby API",
            source="ashby",
        )

        result = await collector.execute(query)

        assert result.success is False
        assert len(result.errors) >= 1

    @patch("app.collectors.plugins.ashby.collector.RetryStrategy.execute")
    async def test_404_error(
        self,
        mock_retry_execute: AsyncMock,
        collector: AshbyCollector,
        query: CollectorQuery,
    ) -> None:
        from app.collectors.exceptions import NetworkError

        mock_retry_execute.side_effect = NetworkError(
            "Ashby board 'exampleco' not found (HTTP 404)",
            status_code=404,
            source="ashby",
        )

        result = await collector.execute(query)
        assert result.success is False

    @patch("app.collectors.plugins.ashby.collector.RetryStrategy.execute")
    async def test_unexpected_response_format(
        self,
        mock_retry_execute: AsyncMock,
        collector: AshbyCollector,
        query: CollectorQuery,
    ) -> None:
        mock_retry_execute.return_value = _mock_response(json_data=[])

        result = await collector.execute(query)
        assert result.success is False
        assert len(result.errors) >= 1

    @patch("app.collectors.plugins.ashby.collector.RetryStrategy.execute")
    async def test_deduplication(
        self,
        mock_retry_execute: AsyncMock,
        collector: AshbyCollector,
        query: CollectorQuery,
    ) -> None:
        job1 = _sample_posting("abc123", title="Unique Job")
        job2 = _sample_posting("def456", title="Another Job")

        mock_retry_execute.return_value = _mock_response(
            json_data={"jobs": [job1, job2]}
        )

        result = await collector.execute(query)

        assert result.success is True
        assert len(result.jobs) == 2
        assert result.stats.total_duplicates_removed == 0

    @patch("app.collectors.plugins.ashby.collector.RetryStrategy.execute")
    async def test_validation_removes_invalid(
        self,
        mock_retry_execute: AsyncMock,
        collector: AshbyCollector,
        query: CollectorQuery,
    ) -> None:
        valid_job = _sample_posting("abc123", title="Valid Job")
        no_title = _sample_posting("no-title", title="")
        no_url = _sample_posting("no-url", title="No URL")
        no_url["postingUrl"] = ""

        mock_retry_execute.return_value = _mock_response(
            json_data={"jobs": [valid_job, no_title, no_url]},
        )

        result = await collector.execute(query)

        assert result.success is True
        assert len(result.jobs) == 1
        assert result.jobs[0].title == "Valid Job"
        assert result.stats.total_normalized == 3
        assert result.stats.total_valid == 1
        assert result.stats.total_saved == 1

    @patch("app.collectors.plugins.ashby.collector.RetryStrategy.execute")
    async def test_remote_location_parsing(
        self,
        mock_retry_execute: AsyncMock,
        collector: AshbyCollector,
        query: CollectorQuery,
    ) -> None:
        job = _sample_posting("abc123", title="Remote Engineer", remote=True)

        mock_retry_execute.return_value = _mock_response(json_data={"jobs": [job]})

        result = await collector.execute(query)

        assert result.success is True
        assert len(result.jobs) == 1
        assert result.jobs[0].location.remote_type == "remote"
        assert result.jobs[0].location.country == "United States"

    @patch("app.collectors.plugins.ashby.collector.RetryStrategy.execute")
    async def test_compensation_extraction(
        self,
        mock_retry_execute: AsyncMock,
        collector: AshbyCollector,
        query: CollectorQuery,
    ) -> None:
        job = _sample_posting("abc123", title="Paid Job", include_compensation=True)

        mock_retry_execute.return_value = _mock_response(json_data={"jobs": [job]})

        result = await collector.execute(query)

        assert result.success is True
        assert result.jobs[0].salary is not None
        assert result.jobs[0].salary.min == 100000
        assert result.jobs[0].salary.max == 150000
        assert result.jobs[0].salary.currency == "USD"

    @patch("app.collectors.plugins.ashby.collector.RetryStrategy.execute")
    async def test_missing_fields_handled(
        self,
        mock_retry_execute: AsyncMock,
        collector: AshbyCollector,
        query: CollectorQuery,
    ) -> None:
        minimal_posting: dict[str, Any] = {
            "id": "min123",
            "title": "Minimal Job",
            "postingUrl": "https://jobs.ashbyhq.com/exampleco/min123",
        }

        mock_retry_execute.return_value = _mock_response(
            json_data={"jobs": [minimal_posting]}
        )

        result = await collector.execute(query)

        assert result.success is True
        assert len(result.jobs) == 1
        assert result.jobs[0].title == "Minimal Job"
        assert result.jobs[0].company.name == "Exampleco"
        assert result.jobs[0].location.remote_type == "onsite"
        assert result.jobs[0].employment_type is None
        assert result.jobs[0].salary is None

    @patch("app.collectors.plugins.ashby.collector.RetryStrategy.execute")
    async def test_is_listed_filter(
        self,
        mock_retry_execute: AsyncMock,
        collector: AshbyCollector,
        query: CollectorQuery,
    ) -> None:
        listed_job = _sample_posting("abc123", title="Listed Job", listed=True)
        unlisted_job = _sample_posting("def456", title="Unlisted Job", listed=False)
        no_field_job = _sample_posting("ghi789", title="No Field Job")

        mock_retry_execute.return_value = _mock_response(
            json_data={"jobs": [listed_job, unlisted_job, no_field_job]},
        )

        result = await collector.execute(query)

        assert result.success is True
        assert len(result.jobs) == 2
        titles = {j.title for j in result.jobs}
        assert "Listed Job" in titles
        assert "No Field Job" in titles
        assert "Unlisted Job" not in titles

    @patch("app.collectors.plugins.ashby.collector.RetryStrategy.execute")
    async def test_cleanup_releases_resources(
        self,
        mock_retry_execute: AsyncMock,
        collector: AshbyCollector,
        query: CollectorQuery,
    ) -> None:
        mock_retry_execute.return_value = _mock_response(json_data={"jobs": []})

        await collector.execute(query)

        assert collector._client is None
        assert collector._initialized is False

    @patch("app.collectors.plugins.ashby.collector.RetryStrategy.execute")
    async def test_cleanup_idempotent(
        self,
        mock_retry_execute: AsyncMock,
        collector: AshbyCollector,
        query: CollectorQuery,
    ) -> None:
        await collector.cleanup()
        await collector.cleanup()

    @patch("app.collectors.plugins.ashby.collector.RetryStrategy.execute")
    async def test_normalize_with_empty_raw_data(
        self,
        mock_retry_execute: AsyncMock,
        collector: AshbyCollector,
        query: CollectorQuery,
    ) -> None:
        result = await collector.normalize({})
        assert result == []

        result = await collector.normalize({"jobs": []})
        assert result == []

        result = await collector.normalize(None)
        assert result == []

    @patch("app.collectors.plugins.ashby.collector.RetryStrategy.execute")
    async def test_board_token_from_additional_filters(
        self,
        mock_retry_execute: AsyncMock,
        collector: AshbyCollector,
    ) -> None:
        custom_query = CollectorQuery(
            additional_filters={"board_token": "acmecorp"},
        )
        job = _sample_posting("abc123", title="Acme Job")

        mock_retry_execute.return_value = _mock_response(json_data={"jobs": [job]})

        result = await collector.execute(custom_query)
        assert result.success is True
        assert result.jobs[0].company.name == "ExampleCo"

        expected_url = f"{ASHBY_API_BASE}/acmecorp?includeCompensation=true"
        mock_retry_execute.assert_called_with(
            collector._fetch_page,
            expected_url,
        )

    @patch("app.collectors.plugins.ashby.collector.RetryStrategy.execute")
    async def test_company_name_falls_back_to_board_token(
        self,
        mock_retry_execute: AsyncMock,
        collector: AshbyCollector,
    ) -> None:
        custom_query = CollectorQuery(
            additional_filters={"board_token": "acmecorp"},
        )
        job = _sample_posting("abc123", title="Acme Job")
        job["companyName"] = ""

        mock_retry_execute.return_value = _mock_response(json_data={"jobs": [job]})

        result = await collector.execute(custom_query)
        assert result.success is True
        assert result.jobs[0].company.name == "Acmecorp"

    @patch("app.collectors.plugins.ashby.collector.RetryStrategy.execute")
    async def test_initialize_sets_up_client(
        self,
        mock_retry_execute: AsyncMock,
        collector: AshbyCollector,
    ) -> None:
        assert collector._client is None
        assert collector._initialized is False

        await collector.initialize()

        assert collector._client is not None
        assert collector._initialized is True
        await collector.cleanup()

    @patch("app.collectors.plugins.ashby.collector.RetryStrategy.execute")
    async def test_compensation_without_min_max(
        self,
        mock_retry_execute: AsyncMock,
        collector: AshbyCollector,
        query: CollectorQuery,
    ) -> None:
        job = _sample_posting("abc123", title="Flat Rate Job")
        job["compensationSummary"] = "$80,000"

        mock_retry_execute.return_value = _mock_response(json_data={"jobs": [job]})

        result = await collector.execute(query)
        assert result.success is True
        assert result.jobs[0].salary is not None
        assert result.jobs[0].salary.min == 80000
        assert result.jobs[0].salary.max is None

    @patch("app.collectors.plugins.ashby.collector.RetryStrategy.execute")
    async def test_compensation_parses_interval(
        self,
        mock_retry_execute: AsyncMock,
        collector: AshbyCollector,
        query: CollectorQuery,
    ) -> None:
        job = _sample_posting("abc123", title="Hourly Job")
        job["compensationSummary"] = "$50 - $75 per hour"

        mock_retry_execute.return_value = _mock_response(json_data={"jobs": [job]})

        result = await collector.execute(query)
        assert result.success is True
        assert result.jobs[0].salary is not None
        assert result.jobs[0].salary.min == 50
        assert result.jobs[0].salary.max == 75
        assert result.jobs[0].salary.interval == "hourly"

    @patch("app.collectors.plugins.ashby.collector.RetryStrategy.execute")
    async def test_department_mapped_to_skills(
        self,
        mock_retry_execute: AsyncMock,
        collector: AshbyCollector,
        query: CollectorQuery,
    ) -> None:
        job = _sample_posting(
            "abc123",
            title="Engineer",
            department="Platform Engineering",
        )

        mock_retry_execute.return_value = _mock_response(json_data={"jobs": [job]})

        result = await collector.execute(query)
        assert result.success is True
        assert "Platform Engineering" in result.jobs[0].skills

    @patch("app.collectors.plugins.ashby.collector.RetryStrategy.execute")
    async def test_timeout_handling(
        self,
        mock_retry_execute: AsyncMock,
        collector: AshbyCollector,
        query: CollectorQuery,
    ) -> None:
        from app.collectors.exceptions import NetworkError

        mock_retry_execute.side_effect = NetworkError(
            "Request to Ashby API timed out",
            source="ashby",
        )

        result = await collector.execute(query)

        assert result.success is False
        assert len(result.errors) >= 1

    def test_parse_location_various_formats(
        self,
        collector: AshbyCollector,
    ) -> None:
        loc = collector._parse_location("San Francisco, CA")
        assert loc.city == "San Francisco"
        assert loc.state == "CA"
        assert loc.country is None
        assert loc.remote_type == "onsite"

        loc = collector._parse_location("New York, NY, United States")
        assert loc.city == "New York"
        assert loc.state == "NY"
        assert loc.country == "United States"

        loc = collector._parse_location("Remote")
        assert loc.remote_type == "remote"
        assert loc.city is None

        loc = collector._parse_location("Remote, Canada")
        assert loc.remote_type == "remote"
        assert loc.country == "Canada"

        loc = collector._parse_location("Remote - North America")
        assert loc.remote_type == "remote"
        assert loc.country == "North America"

        loc = collector._parse_location("")
        assert loc.remote_type == "onsite"
        assert loc.city is None

    def test_parse_compensation_various_formats(
        self,
        collector: AshbyCollector,
    ) -> None:
        salary = collector._parse_compensation("$100,000 - $150,000 USD")
        assert salary is not None
        assert salary.min == 100000
        assert salary.max == 150000
        assert salary.currency == "USD"

        salary = collector._parse_compensation("$80,000")
        assert salary is not None
        assert salary.min == 80000
        assert salary.max is None

        salary = collector._parse_compensation("Not specified")
        assert salary is None

        salary = collector._parse_compensation(None)
        assert salary is None

        salary = collector._parse_compensation("€60,000 - €80,000 EUR")
        assert salary is not None
        assert salary.min == 60000
        assert salary.max == 80000
        assert salary.currency == "EUR"

    @patch("app.collectors.plugins.ashby.collector.RetryStrategy.execute")
    async def test_registry_integration(
        self,
        mock_retry_execute: AsyncMock,
    ) -> None:
        from app.collectors.registry import CollectorRegistry

        cls = CollectorRegistry.get("ashby")
        assert cls is not None
        assert cls is AshbyCollector

        names = CollectorRegistry.list_collectors()
        assert "ashby" in names

    @patch("app.collectors.plugins.ashby.collector.RetryStrategy.execute")
    async def test_collector_name_and_source_id(
        self,
        mock_retry_execute: AsyncMock,
        collector: AshbyCollector,
    ) -> None:
        assert collector.name == "ashby"
        assert collector.source_id == "ashby"
