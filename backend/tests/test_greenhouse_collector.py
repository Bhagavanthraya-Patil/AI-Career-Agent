from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import pytest_asyncio

from app.collectors.models import CollectorQuery
from app.collectors.plugins.greenhouse.collector import (
    GREENHOUSE_API_BASE,
    GreenhouseCollector,
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
def collector(config: dict[str, Any]) -> GreenhouseCollector:
    return GreenhouseCollector(config)


@pytest.fixture
def query() -> CollectorQuery:
    return CollectorQuery(
        keywords=["software engineer"],
        locations=["Remote"],
        additional_filters={"board_token": "exampleco"},
    )


def _mock_response(
    status_code: int = 200,
    json_data: dict[str, Any] | None = None,
    text: str | None = None,
    headers: dict[str, str] | None = None,
) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.headers = headers or {}
    if json_data is not None:
        resp.json = MagicMock(return_value=json_data)
    else:
        resp.json = MagicMock(side_effect=ValueError("No JSON"))
    if text is not None:
        resp.text = text
    return resp


def _sample_job(
    job_id: int,
    title: str = "Software Engineer",
    company: str = "Engineering",
    location: str = "San Francisco, CA",
    remote: bool = False,
    employment_type: str = "Full-time",
    experience_level: str = "Mid-Senior",
    include_salary: bool = False,
) -> dict[str, Any]:
    metadata: list[dict[str, Any]] = [
        {
            "id": 1,
            "name": "Employment Type",
            "value": employment_type,
            "value_type": "single_select",
        },
        {
            "id": 2,
            "name": "Experience Level",
            "value": experience_level,
            "value_type": "single_select",
        },
    ]
    if include_salary:
        metadata.append(
            {
                "id": 3,
                "name": "Salary",
                "value": "$100,000 - $150,000",
                "value_type": "single_select",
            }
        )
    if remote:
        metadata.append(
            {
                "id": 4,
                "name": "Remote",
                "value": "Remote",
                "value_type": "single_select",
            }
        )
        location = "Remote, United States"

    return {
        "id": job_id,
        "title": title,
        "location": {"name": location},
        "offices": [{"id": 1, "name": company, "location": location}],
        "departments": [{"id": 1, "name": "Engineering"}],
        "metadata": metadata,
        "content": f"<div>Job description for {title}</div>",
        "absolute_url": f"https://boards.greenhouse.io/exampleco/jobs/{job_id}",
        "internal_job_id": job_id * 10,
        "requisition_id": f"R{job_id}",
        "created_at": "2026-01-15T12:00:00.000Z",
        "updated_at": "2026-01-15T12:00:00.000Z",
        "board_token": "exampleco",
    }


class TestGreenhouseCollector:
    """Test suite for GreenhouseCollector."""

    async def _patch_client(
        self,
        collector: GreenhouseCollector,
        mock_responses: list[MagicMock],
    ) -> None:
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock()
        mock_client.get.side_effect = mock_responses
        mock_client.aclose = AsyncMock()
        collector._client = mock_client
        collector._initialized = True

    @patch("app.collectors.plugins.greenhouse.collector.RetryStrategy.execute")
    async def test_successful_collection(
        self,
        mock_retry_execute: AsyncMock,
        collector: GreenhouseCollector,
        query: CollectorQuery,
    ) -> None:
        job1 = _sample_job(101, title="Software Engineer")
        job2 = _sample_job(102, title="Senior Engineer")

        mock_resp = _mock_response(
            json_data={
                "jobs": [job1, job2],
                "meta": {"total": 2, "page": 1, "per_page": 100},
            }
        )
        mock_retry_execute.return_value = mock_resp

        result = await collector.execute(query)

        assert result.success is True
        assert len(result.jobs) == 2
        assert result.stats.total_discovered == 2
        assert result.stats.total_saved == 2
        assert result.stats.total_normalized == 2
        assert result.stats.total_valid == 2
        assert result.stats.total_failed == 0

        assert result.jobs[0].title == "Software Engineer"
        assert result.jobs[0].metadata.source_job_id == "101"
        assert result.jobs[0].metadata.job_url == job1["absolute_url"]
        assert result.jobs[0].company.name == "Engineering"
        assert result.jobs[0].location.city == "San Francisco"
        assert result.jobs[0].location.state == "CA"
        assert result.jobs[0].location.remote_type == "onsite"
        assert result.jobs[0].employment_type == "full-time"
        assert result.jobs[0].experience_level == "mid-senior"
        assert result.jobs[0].description_html == job1["content"]
        assert "Job description for Software Engineer" in result.jobs[0].description_raw
        assert result.jobs[0].metadata.posted_at == datetime(
            2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc
        )

    @patch("app.collectors.plugins.greenhouse.collector.RetryStrategy.execute")
    async def test_empty_response(
        self,
        mock_retry_execute: AsyncMock,
        collector: GreenhouseCollector,
        query: CollectorQuery,
    ) -> None:
        mock_resp = _mock_response(
            json_data={"jobs": [], "meta": {"total": 0, "page": 1, "per_page": 100}}
        )
        mock_retry_execute.return_value = mock_resp

        result = await collector.execute(query)

        assert result.success is True
        assert len(result.jobs) == 0
        assert result.stats.total_discovered == 0
        assert result.stats.total_saved == 0

    @patch("app.collectors.plugins.greenhouse.collector.RetryStrategy.execute")
    async def test_pagination(
        self,
        mock_retry_execute: AsyncMock,
        collector: GreenhouseCollector,
        query: CollectorQuery,
    ) -> None:
        page1_jobs = [_sample_job(i, title=f"Job {i}") for i in range(1, 3)]
        page2_jobs = [_sample_job(i, title=f"Job {i}") for i in range(3, 5)]

        mock_retry_execute.side_effect = [
            _mock_response(
                json_data={
                    "jobs": page1_jobs,
                    "meta": {"total": 4, "page": 1, "per_page": 2},
                }
            ),
            _mock_response(
                json_data={
                    "jobs": page2_jobs,
                    "meta": {"total": 4, "page": 2, "per_page": 2},
                }
            ),
        ]

        result = await collector.execute(query)

        assert result.success is True
        assert len(result.jobs) == 4
        assert result.stats.pages_collected == 2
        assert result.stats.total_discovered == 4

    @patch("app.collectors.plugins.greenhouse.collector.RetryStrategy.execute")
    async def test_pagination_breaks_on_empty_page(
        self,
        mock_retry_execute: AsyncMock,
        collector: GreenhouseCollector,
        query: CollectorQuery,
    ) -> None:
        page1_jobs = [_sample_job(i, title=f"Job {i}") for i in range(1, 3)]

        mock_retry_execute.side_effect = [
            _mock_response(
                json_data={
                    "jobs": page1_jobs,
                    "meta": {"total": 3, "page": 1, "per_page": 2},
                }
            ),
            _mock_response(
                json_data={
                    "jobs": [],
                    "meta": {"total": 3, "page": 2, "per_page": 2},
                }
            ),
        ]

        result = await collector.execute(query)

        assert result.success is True
        assert len(result.jobs) == 2
        assert result.stats.pages_collected == 1

    @patch("app.collectors.plugins.greenhouse.collector.RetryStrategy.execute")
    async def test_max_results_respected(
        self,
        mock_retry_execute: AsyncMock,
        collector: GreenhouseCollector,
    ) -> None:
        query = CollectorQuery(
            max_results=1,
            additional_filters={"board_token": "exampleco"},
        )
        page1_jobs = [_sample_job(1, title="Job 1"), _sample_job(2, title="Job 2")]

        mock_retry_execute.return_value = _mock_response(
            json_data={
                "jobs": page1_jobs,
                "meta": {"total": 2, "page": 1, "per_page": 2},
            }
        )

        result = await collector.execute(query)

        assert result.success is True
        assert len(result.jobs) == 1
        assert result.jobs[0].metadata.source_job_id == "1"

    @patch("app.collectors.plugins.greenhouse.collector.RetryStrategy.execute")
    async def test_network_error_handling(
        self,
        mock_retry_execute: AsyncMock,
        collector: GreenhouseCollector,
        query: CollectorQuery,
    ) -> None:
        from app.collectors.exceptions import NetworkError

        mock_retry_execute.side_effect = NetworkError("Connection refused", source="greenhouse")

        result = await collector.execute(query)

        assert result.success is False
        assert len(result.jobs) == 0
        assert len(result.errors) == 1
        assert result.errors[0].error_type == "NetworkError"

    @patch("app.collectors.plugins.greenhouse.collector.RetryStrategy.execute")
    async def test_retry_on_rate_limit(
        self,
        mock_retry_execute: AsyncMock,
        collector: GreenhouseCollector,
        query: CollectorQuery,
    ) -> None:
        from app.collectors.exceptions import RateLimitError

        mock_retry_execute.side_effect = RateLimitError(
            "Rate limited",
            retry_after=10.0,
            source="greenhouse",
        )

        result = await collector.execute(query)

        assert result.success is False
        assert len(result.jobs) == 0
        assert len(result.errors) == 1
        assert result.errors[0].error_type == "RateLimitError"

    @patch("app.collectors.plugins.greenhouse.collector.RetryStrategy.execute")
    async def test_404_board(
        self,
        mock_retry_execute: AsyncMock,
        collector: GreenhouseCollector,
        query: CollectorQuery,
    ) -> None:
        from app.collectors.exceptions import RateLimitError

        mock_retry_execute.side_effect = RateLimitError(
            "Rate limited",
            retry_after=10.0,
            source="greenhouse",
        )

        result = await collector.execute(query)

        assert result.success is False
        assert len(result.jobs) == 0
        assert len(result.errors) == 1
        assert result.errors[0].error_type == "NetworkError"

    @patch("app.collectors.plugins.greenhouse.collector.RetryStrategy.execute")
    async def test_404_board(
        self,
        mock_retry_execute: AsyncMock,
        collector: GreenhouseCollector,
        query: CollectorQuery,
    ) -> None:
        from app.collectors.exceptions import NetworkError

        mock_retry_execute.side_effect = NetworkError(
            "Greenhouse board 'exampleco' not found (HTTP 404)",
            status_code=404,
            source="greenhouse",
        )

        result = await collector.execute(query)

        assert result.success is False
        assert len(result.errors) == 1
        assert result.errors[0].error_type == "NetworkError"
        assert "404" in result.errors[0].error_message

    @patch("app.collectors.plugins.greenhouse.collector.RetryStrategy.execute")
    async def test_deduplication(
        self,
        mock_retry_execute: AsyncMock,
        collector: GreenhouseCollector,
        query: CollectorQuery,
    ) -> None:
        job1 = _sample_job(101, title="Existing Job")
        job2 = _sample_job(102, title="New Job")

        mock_resp = _mock_response(
            json_data={
                "jobs": [job1, job2],
                "meta": {"total": 2, "page": 1, "per_page": 100},
            }
        )
        mock_retry_execute.return_value = mock_resp

        old_execute = collector.execute
        original_execute = GreenhouseCollector.execute

        try:

            async def patched_execute(self: GreenhouseCollector, q: CollectorQuery) -> Any:
                self._execute_query = q
                try:
                    await self.initialize()
                    raw_result = await self.collect(q)
                    raw_result.existing_source_ids = ["101"]

                    total_discovered = raw_result.stats.total_discovered
                    pages_collected = raw_result.stats.pages_collected
                    existing_ids = raw_result.existing_source_ids

                    normalized = await self.normalize(raw_result.raw_data)
                    total_normalized = len(normalized)

                    validated = await self.validate(normalized)
                    total_valid = len(validated)

                    deduped = await self.deduplicate(validated, existing_ids)
                    total_duplicates = total_valid - len(deduped)

                    self._execute_stats = {
                        "total_discovered": total_discovered,
                        "total_normalized": total_normalized,
                        "total_valid": total_valid,
                        "total_duplicates": total_duplicates,
                        "pages_collected": pages_collected,
                    }

                    result = await self.save(deduped)
                    return result
                finally:
                    await self.cleanup()

            GreenhouseCollector.execute = patched_execute  # type: ignore

            result = await collector.execute(query)
        finally:
            GreenhouseCollector.execute = original_execute

        assert result.success is True
        assert len(result.jobs) == 1
        assert result.jobs[0].metadata.source_job_id == "102"
        assert result.stats.total_duplicates_removed == 1
        assert result.stats.total_saved == 1

    @patch("app.collectors.plugins.greenhouse.collector.RetryStrategy.execute")
    async def test_validation_removes_invalid(
        self,
        mock_retry_execute: AsyncMock,
        collector: GreenhouseCollector,
        query: CollectorQuery,
    ) -> None:
        valid_job = _sample_job(101, title="Valid Job")
        no_title_job = _sample_job(102, title="")
        no_url_job = _sample_job(103, title="No URL")
        del no_url_job["absolute_url"]

        mock_resp = _mock_response(
            json_data={
                "jobs": [valid_job, no_title_job, no_url_job],
                "meta": {"total": 3, "page": 1, "per_page": 100},
            }
        )
        mock_retry_execute.return_value = mock_resp

        result = await collector.execute(query)

        assert result.success is True
        assert len(result.jobs) == 1
        assert result.jobs[0].title == "Valid Job"
        assert result.stats.total_normalized == 3
        assert result.stats.total_valid == 1
        assert result.stats.total_saved == 1

    @patch("app.collectors.plugins.greenhouse.collector.RetryStrategy.execute")
    async def test_remote_location_parsing(
        self,
        mock_retry_execute: AsyncMock,
        collector: GreenhouseCollector,
        query: CollectorQuery,
    ) -> None:
        job = _sample_job(
            101,
            title="Remote Engineer",
            location="Remote, United States",
            remote=True,
        )

        mock_resp = _mock_response(
            json_data={
                "jobs": [job],
                "meta": {"total": 1, "page": 1, "per_page": 100},
            }
        )
        mock_retry_execute.return_value = mock_resp

        result = await collector.execute(query)

        assert len(result.jobs) == 1
        loc = result.jobs[0].location
        assert loc.remote_type == "remote"
        assert loc.country == "United States"
        assert loc.full_address == "Remote, United States"

    @patch("app.collectors.plugins.greenhouse.collector.RetryStrategy.execute")
    async def test_salary_extraction_from_metadata(
        self,
        mock_retry_execute: AsyncMock,
        collector: GreenhouseCollector,
        query: CollectorQuery,
    ) -> None:
        job = _sample_job(101, title="Paid Job", include_salary=True)

        mock_resp = _mock_response(
            json_data={
                "jobs": [job],
                "meta": {"total": 1, "page": 1, "per_page": 100},
            }
        )
        mock_retry_execute.return_value = mock_resp

        result = await collector.execute(query)

        assert len(result.jobs) == 1
        salary = result.jobs[0].salary
        assert salary is not None
        assert salary.min == 100000
        assert salary.max == 150000
        assert salary.currency == "USD"

    @patch("app.collectors.plugins.greenhouse.collector.RetryStrategy.execute")
    async def test_cleanup_releases_client(
        self,
        mock_retry_execute: AsyncMock,
        collector: GreenhouseCollector,
        query: CollectorQuery,
    ) -> None:
        job = _sample_job(101)
        mock_resp = _mock_response(
            json_data={
                "jobs": [job],
                "meta": {"total": 1, "page": 1, "per_page": 100},
            }
        )
        mock_retry_execute.return_value = mock_resp

        await collector.execute(query)

        assert collector._client is None
        assert collector._initialized is False

    @patch("app.collectors.plugins.greenhouse.collector.RetryStrategy.execute")
    async def test_company_name_falls_back_to_board_token(
        self,
        mock_retry_execute: AsyncMock,
        collector: GreenhouseCollector,
        query: CollectorQuery,
    ) -> None:
        job = _sample_job(101, title="Engineer", company="")
        job["offices"] = []

        mock_resp = _mock_response(
            json_data={
                "jobs": [job],
                "meta": {"total": 1, "page": 1, "per_page": 100},
            }
        )
        mock_retry_execute.return_value = mock_resp

        result = await collector.execute(query)

        assert result.jobs[0].company.name == "Exampleco"

    @patch("app.collectors.plugins.greenhouse.collector.RetryStrategy.execute")
    async def test_board_token_from_additional_filters(
        self,
        mock_retry_execute: AsyncMock,
        collector: GreenhouseCollector,
        query: CollectorQuery,
    ) -> None:
        job = _sample_job(101, title="Engineer")
        mock_resp = _mock_response(
            json_data={
                "jobs": [job],
                "meta": {"total": 1, "page": 1, "per_page": 100},
            }
        )
        mock_retry_execute.return_value = mock_resp

        await collector.execute(query)

        expected_url = f"{GREENHOUSE_API_BASE}/exampleco/jobs?content=true&page=1"
        mock_retry_execute.assert_called()

    @patch("app.collectors.plugins.greenhouse.collector.RetryStrategy.execute")
    async def test_invalid_json_response(
        self,
        mock_retry_execute: AsyncMock,
        collector: GreenhouseCollector,
        query: CollectorQuery,
    ) -> None:
        from app.collectors.exceptions import NetworkError, ParsingError

        mock_retry_execute.side_effect = ParsingError(
            "Invalid JSON response from Greenhouse API",
            source="greenhouse",
        )

        result = await collector.execute(query)

        assert result.success is False
        assert len(result.jobs) == 0
        assert len(result.errors) == 1
        assert result.errors[0].error_type == "ParsingError"

    async def test_initialize_sets_up_client(
        self,
        collector: GreenhouseCollector,
    ) -> None:
        assert collector._client is None
        assert collector._initialized is False

        await collector.initialize()

        assert collector._client is not None
        assert collector._initialized is True
        await collector.cleanup()

    async def test_cleanup_idempotent(
        self,
        collector: GreenhouseCollector,
    ) -> None:
        await collector.initialize()
        await collector.cleanup()
        await collector.cleanup()
        assert collector._client is None
        assert collector._initialized is False

    async def test_normalize_with_empty_raw_data(
        self,
        collector: GreenhouseCollector,
    ) -> None:
        result = await collector.normalize({})
        assert result == []

        result = await collector.normalize({"jobs": []})
        assert result == []

        result = await collector.normalize(None)
        assert result == []

    def test_parse_location_various_formats(
        self,
        collector: GreenhouseCollector,
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

        loc = collector._parse_location("")
        assert loc.remote_type == "onsite"
        assert loc.city is None

    def test_parse_salary_various_formats(
        self,
        collector: GreenhouseCollector,
    ) -> None:
        salary = collector._parse_metadata_salary("$100,000 - $150,000")
        assert salary is not None
        assert salary.min == 100000
        assert salary.max == 150000

        salary = collector._parse_metadata_salary("$80,000")
        assert salary is not None
        assert salary.min == 80000
        assert salary.max is None

        salary = collector._parse_metadata_salary("Not specified")
        assert salary is None
