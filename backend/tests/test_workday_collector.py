from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import pytest_asyncio

from app.collectors.models import CollectorQuery
from app.collectors.plugins.workday.collector import WorkdayCollector


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
def collector(config: dict[str, Any]) -> WorkdayCollector:
    return WorkdayCollector(config)


@pytest.fixture
def query() -> CollectorQuery:
    return CollectorQuery(
        keywords=["software engineer"],
        locations=["Remote"],
        additional_filters={"tenant": "exampleco"},
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
    job_id: str = "R12345",
    title: str = "Software Engineer",
    location: str = "San Francisco, CA, United States",
    company: str = "ExampleCo",
    remote: bool = False,
    hybrid: bool = False,
    employment_type: str = "Full-time",
) -> dict[str, Any]:
    bullet_fields: list[str] = [employment_type, "Individual Contributor"]
    loc = location
    if remote:
        bullet_fields.append("Remote")
        loc = "Remote, United States"
    if hybrid:
        bullet_fields.append("Hybrid")
        loc = "San Francisco, CA, United States"

    return {
        "title": title,
        "location": loc,
        "postedOn": "2026-01-15T12:00:00.000Z",
        "externalPath": f"/{title.replace(' ', '-')}_{job_id}",
        "bulletFields": bullet_fields,
        "jobPostingInfo": {
            "jobDescription": f"<div>Job description for {title}</div>",
        },
        "company": company,
    }


class TestWorkdayCollector:
    """Test suite for WorkdayCollector."""

    async def _patch_client(
        self,
        collector: WorkdayCollector,
        mock_responses: list[MagicMock],
    ) -> None:
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock()
        mock_client.post.side_effect = mock_responses
        mock_client.aclose = AsyncMock()
        collector._client = mock_client
        collector._initialized = True

    @patch("app.collectors.plugins.workday.collector.RetryStrategy.execute")
    async def test_successful_collection(
        self,
        mock_retry_execute: AsyncMock,
        collector: WorkdayCollector,
        query: CollectorQuery,
    ) -> None:
        job1 = _sample_job("R101", title="Software Engineer")
        job2 = _sample_job("R102", title="Senior Engineer")

        mock_resp = _mock_response(
            json_data={
                "total": 2,
                "jobPostings": [job1, job2],
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
        assert result.jobs[0].metadata.source_job_id == "R101"
        assert (
            result.jobs[0].metadata.job_url
            == "https://exampleco.myworkdayjobs.com/Software-Engineer_R101"
        )
        assert result.jobs[0].company.name == "ExampleCo"
        assert result.jobs[0].location.city == "San Francisco"
        assert result.jobs[0].location.state == "CA"
        assert result.jobs[0].location.country == "United States"
        assert result.jobs[0].location.remote_type == "onsite"
        assert result.jobs[0].employment_type == "full-time"
        assert (
            "Job description for Software Engineer"
            in result.jobs[0].description_raw
        )
        assert result.jobs[0].metadata.posted_at == datetime(
            2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc
        )

    @patch("app.collectors.plugins.workday.collector.RetryStrategy.execute")
    async def test_empty_response(
        self,
        mock_retry_execute: AsyncMock,
        collector: WorkdayCollector,
        query: CollectorQuery,
    ) -> None:
        mock_resp = _mock_response(
            json_data={"total": 0, "jobPostings": []}
        )
        mock_retry_execute.return_value = mock_resp

        result = await collector.execute(query)

        assert result.success is True
        assert len(result.jobs) == 0
        assert result.stats.total_discovered == 0
        assert result.stats.total_saved == 0

    @patch("app.collectors.plugins.workday.collector.RetryStrategy.execute")
    async def test_pagination(
        self,
        mock_retry_execute: AsyncMock,
        collector: WorkdayCollector,
        query: CollectorQuery,
    ) -> None:
        page1 = [_sample_job(f"R{i}", title=f"Job {i}") for i in range(1, 3)]
        page2 = [_sample_job(f"R{i}", title=f"Job {i}") for i in range(3, 5)]

        mock_retry_execute.side_effect = [
            _mock_response(
                json_data={"total": 4, "jobPostings": page1}
            ),
            _mock_response(
                json_data={"total": 4, "jobPostings": page2}
            ),
        ]

        result = await collector.execute(query)
        assert result.success is True
        assert len(result.jobs) == 4
        assert result.stats.pages_collected == 2
        assert result.stats.total_discovered == 4

    @patch("app.collectors.plugins.workday.collector.RetryStrategy.execute")
    async def test_pagination_breaks_on_empty_page(
        self,
        mock_retry_execute: AsyncMock,
        collector: WorkdayCollector,
        query: CollectorQuery,
    ) -> None:
        page1 = [_sample_job("R1", title="Job 1"), _sample_job("R2", title="Job 2")]

        mock_retry_execute.side_effect = [
            _mock_response(
                json_data={"total": 3, "jobPostings": page1}
            ),
            _mock_response(
                json_data={"total": 3, "jobPostings": []}
            ),
        ]

        result = await collector.execute(query)
        assert result.success is True
        assert len(result.jobs) == 2
        assert result.stats.pages_collected == 1

    @patch("app.collectors.plugins.workday.collector.RetryStrategy.execute")
    async def test_max_results_respected(
        self,
        mock_retry_execute: AsyncMock,
        collector: WorkdayCollector,
    ) -> None:
        query = CollectorQuery(
            max_results=1,
            additional_filters={"tenant": "exampleco"},
        )
        page1 = [_sample_job("R1", title="Job 1"), _sample_job("R2", title="Job 2")]

        mock_retry_execute.return_value = _mock_response(
            json_data={"total": 2, "jobPostings": page1}
        )

        result = await collector.execute(query)
        assert result.success is True
        assert len(result.jobs) == 1
        assert result.jobs[0].metadata.source_job_id == "R1"

    @patch("app.collectors.plugins.workday.collector.RetryStrategy.execute")
    async def test_network_error_handling(
        self,
        mock_retry_execute: AsyncMock,
        collector: WorkdayCollector,
        query: CollectorQuery,
    ) -> None:
        from app.collectors.exceptions import NetworkError

        mock_retry_execute.side_effect = NetworkError(
            "Connection failed",
            source="workday",
        )

        result = await collector.execute(query)

        assert result.success is False
        assert len(result.jobs) == 0
        assert len(result.errors) >= 1
        assert any("NetworkError" in e.error_type for e in result.errors)

    @patch("app.collectors.plugins.workday.collector.RetryStrategy.execute")
    async def test_retry_on_rate_limit(
        self,
        mock_retry_execute: AsyncMock,
        collector: WorkdayCollector,
        query: CollectorQuery,
    ) -> None:
        from app.collectors.exceptions import RateLimitError

        mock_retry_execute.side_effect = RateLimitError(
            "Rate limited",
            retry_after=1.0,
            source="workday",
        )

        result = await collector.execute(query)

        assert result.success is False
        assert len(result.errors) >= 1
        assert any("RateLimitError" in e.error_type for e in result.errors)

    @patch("app.collectors.plugins.workday.collector.RetryStrategy.execute")
    async def test_invalid_json_response(
        self,
        mock_retry_execute: AsyncMock,
        collector: WorkdayCollector,
        query: CollectorQuery,
    ) -> None:
        from app.collectors.exceptions import ParsingError

        mock_retry_execute.side_effect = ParsingError(
            "Invalid JSON from Workday API",
            source="workday",
        )

        result = await collector.execute(query)

        assert result.success is False
        assert len(result.errors) >= 1

    @patch("app.collectors.plugins.workday.collector.RetryStrategy.execute")
    async def test_403_error(
        self,
        mock_retry_execute: AsyncMock,
        collector: WorkdayCollector,
        query: CollectorQuery,
    ) -> None:
        from app.collectors.exceptions import NetworkError

        mock_retry_execute.side_effect = NetworkError(
            "Workday API returned HTTP 403 (Forbidden)",
            status_code=403,
            source="workday",
        )

        result = await collector.execute(query)
        assert result.success is False

    @patch("app.collectors.plugins.workday.collector.RetryStrategy.execute")
    async def test_deduplication(
        self,
        mock_retry_execute: AsyncMock,
        collector: WorkdayCollector,
        query: CollectorQuery,
    ) -> None:
        job1 = _sample_job("R101", title="Unique Job")
        job2 = _sample_job("R102", title="Duplicate Job")

        mock_resp = _mock_response(
            json_data={
                "total": 2,
                "jobPostings": [job1, job2],
            }
        )
        mock_retry_execute.return_value = mock_resp

        result = await collector.execute(query)

        assert result.success is True
        assert len(result.jobs) == 2
        assert result.stats.total_duplicates_removed == 0

    @patch("app.collectors.plugins.workday.collector.RetryStrategy.execute")
    async def test_validation_removes_invalid(
        self,
        mock_retry_execute: AsyncMock,
        collector: WorkdayCollector,
        query: CollectorQuery,
    ) -> None:
        valid_job = _sample_job("R101", title="Valid Job")
        no_title = _sample_job("R102", title="")
        no_path = _sample_job("R103", title="No URL")
        no_path["externalPath"] = ""

        mock_resp = _mock_response(
            json_data={
                "total": 3,
                "jobPostings": [valid_job, no_title, no_path],
            }
        )
        mock_retry_execute.return_value = mock_resp

        result = await collector.execute(query)

        assert result.success is True
        assert len(result.jobs) == 1
        assert result.jobs[0].title == "Valid Job"

    @patch("app.collectors.plugins.workday.collector.RetryStrategy.execute")
    async def test_remote_location_parsing(
        self,
        mock_retry_execute: AsyncMock,
        collector: WorkdayCollector,
        query: CollectorQuery,
    ) -> None:
        job = _sample_job("R101", title="Remote Engineer", remote=True)

        mock_resp = _mock_response(
            json_data={"total": 1, "jobPostings": [job]}
        )
        mock_retry_execute.return_value = mock_resp

        result = await collector.execute(query)

        assert result.success is True
        assert len(result.jobs) == 1
        assert result.jobs[0].location.remote_type == "remote"
        assert result.jobs[0].location.country == "United States"

    @patch("app.collectors.plugins.workday.collector.RetryStrategy.execute")
    async def test_hybrid_location_parsing(
        self,
        mock_retry_execute: AsyncMock,
        collector: WorkdayCollector,
        query: CollectorQuery,
    ) -> None:
        job = _sample_job("R101", title="Hybrid Engineer", hybrid=True)

        mock_resp = _mock_response(
            json_data={"total": 1, "jobPostings": [job]}
        )
        mock_retry_execute.return_value = mock_resp

        result = await collector.execute(query)

        assert result.success is True
        assert len(result.jobs) == 1
        assert result.jobs[0].location.remote_type == "hybrid"

    @patch("app.collectors.plugins.workday.collector.RetryStrategy.execute")
    async def test_missing_fields_handled(
        self,
        mock_retry_execute: AsyncMock,
        collector: WorkdayCollector,
        query: CollectorQuery,
    ) -> None:
        minimal_job: dict[str, Any] = {
            "title": "Minimal Job",
            "location": "",
            "externalPath": "/Minimal-Job_R999",
        }

        mock_resp = _mock_response(
            json_data={"total": 1, "jobPostings": [minimal_job]}
        )
        mock_retry_execute.return_value = mock_resp

        result = await collector.execute(query)

        assert result.success is True
        assert len(result.jobs) == 1
        assert result.jobs[0].title == "Minimal Job"
        assert result.jobs[0].company.name == "Exampleco"
        assert result.jobs[0].location.remote_type == "onsite"
        assert result.jobs[0].metadata.source_job_id == "R999"
        assert result.jobs[0].description_raw is None

    @patch("app.collectors.plugins.workday.collector.RetryStrategy.execute")
    async def test_cleanup_releases_resources(
        self,
        mock_retry_execute: AsyncMock,
        collector: WorkdayCollector,
        query: CollectorQuery,
    ) -> None:
        mock_resp = _mock_response(
            json_data={"total": 0, "jobPostings": []}
        )
        mock_retry_execute.return_value = mock_resp

        result = await collector.execute(query)

        assert result.success is True
        assert collector._client is None
        assert collector._initialized is False

    @patch("app.collectors.plugins.workday.collector.RetryStrategy.execute")
    async def test_cleanup_idempotent(
        self,
        mock_retry_execute: AsyncMock,
        collector: WorkdayCollector,
        query: CollectorQuery,
    ) -> None:
        mock_resp = _mock_response(
            json_data={"total": 0, "jobPostings": []}
        )
        mock_retry_execute.return_value = mock_resp

        await collector.cleanup()
        await collector.cleanup()

    @patch("app.collectors.plugins.workday.collector.RetryStrategy.execute")
    async def test_normalize_with_empty_raw_data(
        self,
        mock_retry_execute: AsyncMock,
        collector: WorkdayCollector,
        query: CollectorQuery,
    ) -> None:
        result = await collector.normalize({})
        assert result == []

        result = await collector.normalize(None)
        assert result == []

    @patch("app.collectors.plugins.workday.collector.RetryStrategy.execute")
    async def test_job_id_from_external_path(
        self,
        mock_retry_execute: AsyncMock,
        collector: WorkdayCollector,
        query: CollectorQuery,
    ) -> None:
        job = _sample_job("R99999", title="ID Test Job")

        mock_resp = _mock_response(
            json_data={"total": 1, "jobPostings": [job]}
        )
        mock_retry_execute.return_value = mock_resp

        result = await collector.execute(query)
        assert result.jobs[0].metadata.source_job_id == "R99999"

    @patch("app.collectors.plugins.workday.collector.RetryStrategy.execute")
    async def test_tenant_from_additional_filters(
        self,
        mock_retry_execute: AsyncMock,
        collector: WorkdayCollector,
    ) -> None:
        custom_query = CollectorQuery(
            additional_filters={"tenant": "acmecorp"},
        )
        job = _sample_job("R1", title="Acme Job", company="AcmeCorp")

        mock_resp = _mock_response(
            json_data={"total": 1, "jobPostings": [job]}
        )
        mock_retry_execute.return_value = mock_resp

        result = await collector.execute(custom_query)
        assert result.success is True
        assert (
            "acmecorp" in result.jobs[0].metadata.job_url
        )
