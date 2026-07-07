from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import pytest_asyncio

from app.collectors.models import CollectorQuery
from app.collectors.plugins.lever.collector import LEVER_API_BASE, LeverCollector


@pytest_asyncio.fixture(scope="module", autouse=True)
async def auto_create_tables():
    from app.db.session import create_tables

    await create_tables()


@pytest.fixture
def config() -> dict[str, Any]:
    return {
        "limit": 2,
        "max_retries": 1,
        "retry_backoff_factor": 1.0,
        "max_pages_per_source": 3,
    }


@pytest.fixture
def collector(config: dict[str, Any]) -> LeverCollector:
    return LeverCollector(config)


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
    team: str = "Engineering",
    commitment: str = "Full-Time",
    remote: bool = False,
    include_salary: bool = False,
) -> dict[str, Any]:
    posting: dict[str, Any] = {
        "id": posting_id,
        "text": title,
        "categories": {
            "team": team,
            "location": location,
            "commitment": commitment,
        },
        "description": f"<div>Description for {title}</div>",
        "descriptionPlain": f"Plain text description for {title}",
        "lists": [
            {
                "text": "Qualifications",
                "content": "<ul><li>3+ years experience</li></ul>",
                "id": "qual",
            },
        ],
        "additional": "",
        "createdAt": 1736899200000,
        "hostedUrl": f"https://jobs.lever.co/exampleco/{posting_id}",
    }
    if remote:
        posting["categories"]["location"] = "Remote, United States"
    if include_salary:
        posting["additional"] = "Salary range: $100,000 - $150,000 USD"
    return posting


class TestLeverCollector:
    """Test suite for LeverCollector."""

    async def _patch_client(
        self,
        collector: LeverCollector,
        mock_responses: list[MagicMock],
    ) -> None:
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock()
        mock_client.get.side_effect = mock_responses
        mock_client.aclose = AsyncMock()
        collector._client = mock_client
        collector._initialized = True

    @patch("app.collectors.plugins.lever.collector.RetryStrategy.execute")
    async def test_successful_collection(
        self,
        mock_retry_execute: AsyncMock,
        collector: LeverCollector,
        query: CollectorQuery,
    ) -> None:
        job1 = _sample_posting("abc123", title="Software Engineer")
        job2 = _sample_posting("def456", title="Senior Engineer")

        mock_retry_execute.side_effect = [
            _mock_response(json_data=[job1, job2]),
            _mock_response(json_data=[]),
        ]

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
            == "https://jobs.lever.co/exampleco/abc123"
        )
        assert result.jobs[0].company.name == "Engineering"
        assert result.jobs[0].location.city == "San Francisco"
        assert result.jobs[0].location.state == "CA"
        assert result.jobs[0].location.remote_type == "onsite"
        assert result.jobs[0].employment_type == "full-time"
        assert (
            "Plain text description for Software Engineer"
            in result.jobs[0].description_raw
        )
        assert result.jobs[0].metadata.posted_at == datetime(
            2025, 1, 15, 0, 0, tzinfo=timezone.utc
        )

    @patch("app.collectors.plugins.lever.collector.RetryStrategy.execute")
    async def test_empty_response(
        self,
        mock_retry_execute: AsyncMock,
        collector: LeverCollector,
        query: CollectorQuery,
    ) -> None:
        mock_retry_execute.return_value = _mock_response(json_data=[])

        result = await collector.execute(query)

        assert result.success is True
        assert len(result.jobs) == 0
        assert result.stats.total_discovered == 0
        assert result.stats.total_saved == 0

    @patch("app.collectors.plugins.lever.collector.RetryStrategy.execute")
    async def test_pagination(
        self,
        mock_retry_execute: AsyncMock,
        collector: LeverCollector,
        query: CollectorQuery,
    ) -> None:
        page1 = [_sample_posting(f"id{i}", title=f"Job {i}") for i in range(1, 3)]
        page2 = [_sample_posting(f"id{i}", title=f"Job {i}") for i in range(3, 5)]

        mock_retry_execute.side_effect = [
            _mock_response(json_data=page1),
            _mock_response(json_data=page2),
            _mock_response(json_data=[]),
        ]

        result = await collector.execute(query)
        assert result.success is True
        assert len(result.jobs) == 4
        assert result.stats.pages_collected == 2
        assert result.stats.total_discovered == 4

    @patch("app.collectors.plugins.lever.collector.RetryStrategy.execute")
    async def test_pagination_breaks_on_empty_page(
        self,
        mock_retry_execute: AsyncMock,
        collector: LeverCollector,
        query: CollectorQuery,
    ) -> None:
        page1 = [_sample_posting("id1", title="Job 1"), _sample_posting("id2", title="Job 2")]

        mock_retry_execute.side_effect = [
            _mock_response(json_data=page1),
            _mock_response(json_data=[]),
        ]

        result = await collector.execute(query)
        assert result.success is True
        assert len(result.jobs) == 2
        assert result.stats.pages_collected == 1

    @patch("app.collectors.plugins.lever.collector.RetryStrategy.execute")
    async def test_max_results_respected(
        self,
        mock_retry_execute: AsyncMock,
        collector: LeverCollector,
    ) -> None:
        query = CollectorQuery(
            max_results=1,
            additional_filters={"board_token": "exampleco"},
        )
        page1 = [_sample_posting("id1", title="Job 1"), _sample_posting("id2", title="Job 2")]

        mock_retry_execute.return_value = _mock_response(json_data=page1)

        result = await collector.execute(query)
        assert result.success is True
        assert len(result.jobs) == 1
        assert result.jobs[0].metadata.source_job_id == "id1"

    @patch("app.collectors.plugins.lever.collector.RetryStrategy.execute")
    async def test_network_error_handling(
        self,
        mock_retry_execute: AsyncMock,
        collector: LeverCollector,
        query: CollectorQuery,
    ) -> None:
        from app.collectors.exceptions import NetworkError

        mock_retry_execute.side_effect = NetworkError(
            "Connection failed",
            source="lever",
        )

        result = await collector.execute(query)

        assert result.success is False
        assert len(result.jobs) == 0
        assert len(result.errors) >= 1
        assert any("NetworkError" in e.error_type for e in result.errors)

    @patch("app.collectors.plugins.lever.collector.RetryStrategy.execute")
    async def test_retry_on_rate_limit(
        self,
        mock_retry_execute: AsyncMock,
        collector: LeverCollector,
        query: CollectorQuery,
    ) -> None:
        from app.collectors.exceptions import RateLimitError

        mock_retry_execute.side_effect = RateLimitError(
            "Rate limited",
            retry_after=1.0,
            source="lever",
        )

        result = await collector.execute(query)

        assert result.success is False
        assert len(result.errors) >= 1
        assert any("RateLimitError" in e.error_type for e in result.errors)

    @patch("app.collectors.plugins.lever.collector.RetryStrategy.execute")
    async def test_invalid_json_response(
        self,
        mock_retry_execute: AsyncMock,
        collector: LeverCollector,
        query: CollectorQuery,
    ) -> None:
        from app.collectors.exceptions import ParsingError

        mock_retry_execute.side_effect = ParsingError(
            "Invalid JSON from Lever API",
            source="lever",
        )

        result = await collector.execute(query)

        assert result.success is False
        assert len(result.errors) >= 1

    @patch("app.collectors.plugins.lever.collector.RetryStrategy.execute")
    async def test_404_error(
        self,
        mock_retry_execute: AsyncMock,
        collector: LeverCollector,
        query: CollectorQuery,
    ) -> None:
        from app.collectors.exceptions import NetworkError

        mock_retry_execute.side_effect = NetworkError(
            "Lever board 'exampleco' not found (HTTP 404)",
            status_code=404,
            source="lever",
        )

        result = await collector.execute(query)
        assert result.success is False

    @patch("app.collectors.plugins.lever.collector.RetryStrategy.execute")
    async def test_unexpected_response_format(
        self,
        mock_retry_execute: AsyncMock,
        collector: LeverCollector,
        query: CollectorQuery,
    ) -> None:
        mock_retry_execute.return_value = _mock_response(json_data={})

        result = await collector.execute(query)
        assert result.success is False
        assert len(result.errors) >= 1

    @patch("app.collectors.plugins.lever.collector.RetryStrategy.execute")
    async def test_deduplication(
        self,
        mock_retry_execute: AsyncMock,
        collector: LeverCollector,
        query: CollectorQuery,
    ) -> None:
        job1 = _sample_posting("abc123", title="Unique Job")
        job2 = _sample_posting("def456", title="Another Job")

        mock_retry_execute.side_effect = [
            _mock_response(json_data=[job1, job2]),
            _mock_response(json_data=[]),
        ]

        result = await collector.execute(query)

        assert result.success is True
        assert len(result.jobs) == 2
        assert result.stats.total_duplicates_removed == 0

    @patch("app.collectors.plugins.lever.collector.RetryStrategy.execute")
    async def test_validation_removes_invalid(
        self,
        mock_retry_execute: AsyncMock,
        collector: LeverCollector,
        query: CollectorQuery,
    ) -> None:
        valid_job = _sample_posting("abc123", title="Valid Job")
        no_title = _sample_posting("no-title", title="")
        no_url = _sample_posting("no-url", title="No URL")
        no_url["hostedUrl"] = ""

        mock_retry_execute.side_effect = [
            _mock_response(json_data=[valid_job, no_title, no_url]),
            _mock_response(json_data=[]),
        ]

        result = await collector.execute(query)

        assert result.success is True
        assert len(result.jobs) == 1
        assert result.jobs[0].title == "Valid Job"

    @patch("app.collectors.plugins.lever.collector.RetryStrategy.execute")
    async def test_remote_location_parsing(
        self,
        mock_retry_execute: AsyncMock,
        collector: LeverCollector,
        query: CollectorQuery,
    ) -> None:
        job = _sample_posting("abc123", title="Remote Engineer", remote=True)

        mock_retry_execute.side_effect = [
            _mock_response(json_data=[job]),
            _mock_response(json_data=[]),
        ]

        result = await collector.execute(query)

        assert result.success is True
        assert len(result.jobs) == 1
        assert result.jobs[0].location.remote_type == "remote"
        assert result.jobs[0].location.country == "United States"

    @patch("app.collectors.plugins.lever.collector.RetryStrategy.execute")
    async def test_salary_extraction_from_additional(
        self,
        mock_retry_execute: AsyncMock,
        collector: LeverCollector,
        query: CollectorQuery,
    ) -> None:
        job = _sample_posting("abc123", title="Paid Job", include_salary=True)

        mock_retry_execute.side_effect = [
            _mock_response(json_data=[job]),
            _mock_response(json_data=[]),
        ]

        result = await collector.execute(query)

        assert result.success is True
        assert result.jobs[0].salary is not None
        assert result.jobs[0].salary.min == 100000
        assert result.jobs[0].salary.max == 150000
        assert result.jobs[0].salary.currency == "USD"

    @patch("app.collectors.plugins.lever.collector.RetryStrategy.execute")
    async def test_missing_fields_handled(
        self,
        mock_retry_execute: AsyncMock,
        collector: LeverCollector,
        query: CollectorQuery,
    ) -> None:
        minimal_posting: dict[str, Any] = {
            "id": "min123",
            "text": "Minimal Job",
            "categories": {},
            "hostedUrl": "https://jobs.lever.co/exampleco/min123",
        }

        mock_retry_execute.side_effect = [
            _mock_response(json_data=[minimal_posting]),
            _mock_response(json_data=[]),
        ]

        result = await collector.execute(query)

        assert result.success is True
        assert len(result.jobs) == 1
        assert result.jobs[0].title == "Minimal Job"
        assert result.jobs[0].company.name == "Exampleco"
        assert result.jobs[0].location.remote_type == "onsite"
        assert result.jobs[0].employment_type is None
        assert result.jobs[0].salary is None

    @patch("app.collectors.plugins.lever.collector.RetryStrategy.execute")
    async def test_cleanup_releases_resources(
        self,
        mock_retry_execute: AsyncMock,
        collector: LeverCollector,
        query: CollectorQuery,
    ) -> None:
        mock_retry_execute.return_value = _mock_response(json_data=[])

        result = await collector.execute(query)

        assert result.success is True
        assert collector._client is None
        assert collector._initialized is False

    @patch("app.collectors.plugins.lever.collector.RetryStrategy.execute")
    async def test_cleanup_idempotent(
        self,
        mock_retry_execute: AsyncMock,
        collector: LeverCollector,
        query: CollectorQuery,
    ) -> None:
        await collector.cleanup()
        await collector.cleanup()

    @patch("app.collectors.plugins.lever.collector.RetryStrategy.execute")
    async def test_normalize_with_empty_raw_data(
        self,
        mock_retry_execute: AsyncMock,
        collector: LeverCollector,
        query: CollectorQuery,
    ) -> None:
        result = await collector.normalize({})
        assert result == []

        result = await collector.normalize(None)
        assert result == []

    @patch("app.collectors.plugins.lever.collector.RetryStrategy.execute")
    async def test_board_token_from_additional_filters(
        self,
        mock_retry_execute: AsyncMock,
        collector: LeverCollector,
    ) -> None:
        custom_query = CollectorQuery(
            additional_filters={"board_token": "acmecorp"},
        )
        job = _sample_posting("abc123", title="Acme Job")

        mock_retry_execute.side_effect = [
            _mock_response(json_data=[job]),
            _mock_response(json_data=[]),
        ]

        result = await collector.execute(custom_query)
        assert result.success is True
        assert result.jobs[0].company.name == "Engineering"

    @patch("app.collectors.plugins.lever.collector.RetryStrategy.execute")
    async def test_company_name_falls_back_to_board_token(
        self,
        mock_retry_execute: AsyncMock,
        collector: LeverCollector,
    ) -> None:
        custom_query = CollectorQuery(
            additional_filters={"board_token": "acmecorp"},
        )
        job = _sample_posting("abc123", title="Acme Job", team="")

        mock_retry_execute.side_effect = [
            _mock_response(json_data=[job]),
            _mock_response(json_data=[]),
        ]

        result = await collector.execute(custom_query)
        assert result.success is True
        assert result.jobs[0].company.name == "Acmecorp"

    @patch("app.collectors.plugins.lever.collector.RetryStrategy.execute")
    async def test_initialize_sets_up_client(
        self,
        mock_retry_execute: AsyncMock,
        collector: LeverCollector,
    ) -> None:
        assert collector._client is None
        assert collector._initialized is False

        await collector.initialize()

        assert collector._client is not None
        assert collector._initialized is True
        await collector.cleanup()
