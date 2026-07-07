from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import pytest_asyncio

from app.collectors.models import CollectorQuery
from app.collectors.plugins.remoteok.collector import (
    REMOTEOK_API_BASE,
    RemoteOKCollector,
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
def collector(config: dict[str, Any]) -> RemoteOKCollector:
    return RemoteOKCollector(config)


@pytest.fixture
def query() -> CollectorQuery:
    return CollectorQuery(
        keywords=["software engineer"],
        locations=["Remote"],
        additional_filters={},
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


def _sample_job(
    job_id: str = "123456",
    title: str = "Software Engineer",
    company: str = "Acme Corp",
    location: str = "Worldwide",
    tags: list[str] | None = None,
    salary_min: int | None = 100000,
    salary_max: int | None = 150000,
    include_metadata: bool = False,
) -> dict[str, Any]:
    if tags is None:
        tags = ["python", "backend", "full-time"]
    job: dict[str, Any] = {
        "id": job_id,
        "slug": f"remote-{title.lower().replace(' ', '-')}-{job_id}",
        "url": f"https://remoteok.com/remote-jobs/{job_id}-remote-{title.lower().replace(' ', '-')}",
        "title": title,
        "company": company,
        "company_logo": f"https://logo.remoteok.com/{job_id}.png",
        "tags": json.dumps(tags),
        "description": f"<div>Description for {title}</div>",
        "location": location,
        "apply_url": f"https://remoteok.com/remote-jobs/{job_id}/apply",
        "salary_min": salary_min,
        "salary_max": salary_max,
        "date": "2026-01-15T00:00:00.000Z",
        "epoch": 1736899200,
    }
    if include_metadata:
        return {"_metadata": True, "count": 1, "source": "remoteok"}
    return job


def _api_response(
    jobs: list[dict[str, Any]],
    include_meta: bool = True,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    if include_meta:
        result.append(
            {"_metadata": True, "count": len(jobs), "source": "remoteok"}
        )
    result.extend(jobs)
    return result


class TestRemoteOKCollector:
    """Test suite for RemoteOKCollector."""

    @patch("app.collectors.plugins.remoteok.collector.RetryStrategy.execute")
    async def test_successful_collection(
        self,
        mock_retry_execute: AsyncMock,
        collector: RemoteOKCollector,
        query: CollectorQuery,
    ) -> None:
        job1 = _sample_job("123456", title="Software Engineer")
        job2 = _sample_job("789012", title="Senior Engineer")

        mock_retry_execute.return_value = _mock_response(
            json_data=_api_response([job1, job2]),
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
        assert result.jobs[0].metadata.source_job_id == "123456"
        assert (
            result.jobs[0].metadata.job_url
            == "https://remoteok.com/remote-jobs/123456-remote-software-engineer"
        )
        assert result.jobs[0].company.name == "Acme Corp"
        assert result.jobs[0].company.logo_url is not None
        assert result.jobs[0].location.remote_type == "remote"
        assert result.jobs[0].location.country == "Worldwide"
        assert result.jobs[0].employment_type == "full-time"
        assert "Description for Software Engineer" in result.jobs[0].description_raw
        assert result.jobs[0].salary is not None
        assert result.jobs[0].salary.min == 100000
        assert result.jobs[0].salary.max == 150000
        assert result.jobs[0].skills == ["python", "backend", "full-time"]
        assert result.jobs[0].metadata.posted_at == datetime(
            2026, 1, 15, 0, 0, 0, tzinfo=timezone.utc
        )

    @patch("app.collectors.plugins.remoteok.collector.RetryStrategy.execute")
    async def test_empty_response(
        self,
        mock_retry_execute: AsyncMock,
        collector: RemoteOKCollector,
        query: CollectorQuery,
    ) -> None:
        mock_retry_execute.return_value = _mock_response(json_data=[])

        result = await collector.execute(query)

        assert result.success is True
        assert len(result.jobs) == 0
        assert result.stats.total_discovered == 0
        assert result.stats.total_saved == 0

    @patch("app.collectors.plugins.remoteok.collector.RetryStrategy.execute")
    async def test_metadata_first_element_skipped(
        self,
        mock_retry_execute: AsyncMock,
        collector: RemoteOKCollector,
        query: CollectorQuery,
    ) -> None:
        job = _sample_job("123456", title="Engineer")
        meta = {"_metadata": True, "count": 1, "source": "remoteok"}

        mock_retry_execute.return_value = _mock_response(
            json_data=[meta, job],
        )

        result = await collector.execute(query)

        assert result.success is True
        assert len(result.jobs) == 1
        assert result.jobs[0].title == "Engineer"

    @patch("app.collectors.plugins.remoteok.collector.RetryStrategy.execute")
    async def test_meta_only_response(
        self,
        mock_retry_execute: AsyncMock,
        collector: RemoteOKCollector,
        query: CollectorQuery,
    ) -> None:
        meta = {"_metadata": True, "count": 0, "source": "remoteok"}

        mock_retry_execute.return_value = _mock_response(json_data=[meta])

        result = await collector.execute(query)

        assert result.success is True
        assert len(result.jobs) == 0

    @patch("app.collectors.plugins.remoteok.collector.RetryStrategy.execute")
    async def test_max_results_respected(
        self,
        mock_retry_execute: AsyncMock,
        collector: RemoteOKCollector,
    ) -> None:
        query = CollectorQuery(
            max_results=1,
        )
        job1 = _sample_job("1", title="Job 1")
        job2 = _sample_job("2", title="Job 2")

        mock_retry_execute.return_value = _mock_response(
            json_data=_api_response([job1, job2]),
        )

        result = await collector.execute(query)

        assert result.success is True
        assert len(result.jobs) == 1
        assert result.jobs[0].metadata.source_job_id == "1"

    @patch("app.collectors.plugins.remoteok.collector.RetryStrategy.execute")
    async def test_network_error_handling(
        self,
        mock_retry_execute: AsyncMock,
        collector: RemoteOKCollector,
        query: CollectorQuery,
    ) -> None:
        from app.collectors.exceptions import NetworkError

        mock_retry_execute.side_effect = NetworkError(
            "Connection failed",
            source="remoteok",
        )

        result = await collector.execute(query)

        assert result.success is False
        assert len(result.jobs) == 0
        assert len(result.errors) >= 1
        assert any("NetworkError" in e.error_type for e in result.errors)

    @patch("app.collectors.plugins.remoteok.collector.RetryStrategy.execute")
    async def test_retry_on_rate_limit(
        self,
        mock_retry_execute: AsyncMock,
        collector: RemoteOKCollector,
        query: CollectorQuery,
    ) -> None:
        from app.collectors.exceptions import RateLimitError

        mock_retry_execute.side_effect = RateLimitError(
            "Rate limited",
            retry_after=1.0,
            source="remoteok",
        )

        result = await collector.execute(query)

        assert result.success is False
        assert len(result.errors) >= 1
        assert any("RateLimitError" in e.error_type for e in result.errors)

    @patch("app.collectors.plugins.remoteok.collector.RetryStrategy.execute")
    async def test_invalid_json_response(
        self,
        mock_retry_execute: AsyncMock,
        collector: RemoteOKCollector,
        query: CollectorQuery,
    ) -> None:
        from app.collectors.exceptions import ParsingError

        mock_retry_execute.side_effect = ParsingError(
            "Invalid JSON from RemoteOK API",
            source="remoteok",
        )

        result = await collector.execute(query)

        assert result.success is False
        assert len(result.errors) >= 1

    @patch("app.collectors.plugins.remoteok.collector.RetryStrategy.execute")
    async def test_unexpected_response_format(
        self,
        mock_retry_execute: AsyncMock,
        collector: RemoteOKCollector,
        query: CollectorQuery,
    ) -> None:
        mock_retry_execute.return_value = _mock_response(json_data={})

        result = await collector.execute(query)

        assert result.success is False
        assert len(result.errors) >= 1

    @patch("app.collectors.plugins.remoteok.collector.RetryStrategy.execute")
    async def test_deduplication(
        self,
        mock_retry_execute: AsyncMock,
        collector: RemoteOKCollector,
        query: CollectorQuery,
    ) -> None:
        job1 = _sample_job("abc123", title="Unique Job")
        job2 = _sample_job("def456", title="Another Job")

        mock_retry_execute.return_value = _mock_response(
            json_data=_api_response([job1, job2]),
        )

        result = await collector.execute(query)

        assert result.success is True
        assert len(result.jobs) == 2
        assert result.stats.total_duplicates_removed == 0

    @patch("app.collectors.plugins.remoteok.collector.RetryStrategy.execute")
    async def test_validation_removes_invalid(
        self,
        mock_retry_execute: AsyncMock,
        collector: RemoteOKCollector,
        query: CollectorQuery,
    ) -> None:
        valid_job = _sample_job("abc123", title="Valid Job")
        no_title = _sample_job("no-title", title="")
        no_url = _sample_job("no-url", title="No URL")
        no_url["url"] = ""

        mock_retry_execute.return_value = _mock_response(
            json_data=_api_response([valid_job, no_title, no_url]),
        )

        result = await collector.execute(query)

        assert result.success is True
        assert len(result.jobs) == 1
        assert result.jobs[0].title == "Valid Job"
        assert result.stats.total_normalized == 3
        assert result.stats.total_valid == 1
        assert result.stats.total_saved == 1

    @patch("app.collectors.plugins.remoteok.collector.RetryStrategy.execute")
    async def test_remote_location_parsing(
        self,
        mock_retry_execute: AsyncMock,
        collector: RemoteOKCollector,
        query: CollectorQuery,
    ) -> None:
        job = _sample_job(
            "abc123",
            title="Remote Engineer",
            location="United States",
        )

        mock_retry_execute.return_value = _mock_response(
            json_data=_api_response([job]),
        )

        result = await collector.execute(query)

        assert result.success is True
        assert len(result.jobs) == 1
        assert result.jobs[0].location.remote_type == "remote"
        assert result.jobs[0].location.country == "United States"

    @patch("app.collectors.plugins.remoteok.collector.RetryStrategy.execute")
    async def test_salary_parsing(
        self,
        mock_retry_execute: AsyncMock,
        collector: RemoteOKCollector,
        query: CollectorQuery,
    ) -> None:
        job = _sample_job(
            "abc123",
            title="Paid Job",
            salary_min=80000,
            salary_max=120000,
        )

        mock_retry_execute.return_value = _mock_response(
            json_data=_api_response([job]),
        )

        result = await collector.execute(query)

        assert result.success is True
        assert result.jobs[0].salary is not None
        assert result.jobs[0].salary.min == 80000
        assert result.jobs[0].salary.max == 120000
        assert result.jobs[0].salary.currency == "USD"

    @patch("app.collectors.plugins.remoteok.collector.RetryStrategy.execute")
    async def test_zero_salary_treated_as_none(
        self,
        mock_retry_execute: AsyncMock,
        collector: RemoteOKCollector,
        query: CollectorQuery,
    ) -> None:
        job = _sample_job(
            "abc123",
            title="No Salary Job",
            salary_min=0,
            salary_max=0,
        )

        mock_retry_execute.return_value = _mock_response(
            json_data=_api_response([job]),
        )

        result = await collector.execute(query)

        assert result.success is True
        assert result.jobs[0].salary is None

    @patch("app.collectors.plugins.remoteok.collector.RetryStrategy.execute")
    async def test_salary_only_min(
        self,
        mock_retry_execute: AsyncMock,
        collector: RemoteOKCollector,
        query: CollectorQuery,
    ) -> None:
        job = _sample_job(
            "abc123",
            title="Min Only",
            salary_min=75000,
            salary_max=0,
        )

        mock_retry_execute.return_value = _mock_response(
            json_data=_api_response([job]),
        )

        result = await collector.execute(query)

        assert result.success is True
        assert result.jobs[0].salary is not None
        assert result.jobs[0].salary.min == 75000
        assert result.jobs[0].salary.max is None

    @patch("app.collectors.plugins.remoteok.collector.RetryStrategy.execute")
    async def test_tags_parsed_from_json_string(
        self,
        mock_retry_execute: AsyncMock,
        collector: RemoteOKCollector,
        query: CollectorQuery,
    ) -> None:
        job = _sample_job(
            "abc123",
            title="Full Stack Dev",
            tags=["javascript", "react", "node", "full-stack"],
        )

        mock_retry_execute.return_value = _mock_response(
            json_data=_api_response([job]),
        )

        result = await collector.execute(query)

        assert result.success is True
        assert result.jobs[0].skills == [
            "javascript",
            "react",
            "node",
            "full-stack",
        ]

    @patch("app.collectors.plugins.remoteok.collector.RetryStrategy.execute")
    async def test_employment_type_inferred_from_tags(
        self,
        mock_retry_execute: AsyncMock,
        collector: RemoteOKCollector,
        query: CollectorQuery,
    ) -> None:
        contract_job = _sample_job(
            "contract1",
            title="Contract Dev",
            tags=["python", "contract"],
        )

        mock_retry_execute.return_value = _mock_response(
            json_data=_api_response([contract_job]),
        )

        result = await collector.execute(query)

        assert result.jobs[0].employment_type == "contract"

    @patch("app.collectors.plugins.remoteok.collector.RetryStrategy.execute")
    async def test_tags_empty_string_handled(
        self,
        mock_retry_execute: AsyncMock,
        collector: RemoteOKCollector,
        query: CollectorQuery,
    ) -> None:
        job = _sample_job("abc123", title="No Tags Job")
        job["tags"] = ""

        mock_retry_execute.return_value = _mock_response(
            json_data=_api_response([job]),
        )

        result = await collector.execute(query)

        assert result.success is True
        assert result.jobs[0].skills == []

    @patch("app.collectors.plugins.remoteok.collector.RetryStrategy.execute")
    async def test_tags_invalid_json_handled(
        self,
        mock_retry_execute: AsyncMock,
        collector: RemoteOKCollector,
        query: CollectorQuery,
    ) -> None:
        job = _sample_job("abc123", title="Bad Tags Job")
        job["tags"] = "not valid json"

        mock_retry_execute.return_value = _mock_response(
            json_data=_api_response([job]),
        )

        result = await collector.execute(query)

        assert result.success is True
        assert result.jobs[0].skills == []

    @patch("app.collectors.plugins.remoteok.collector.RetryStrategy.execute")
    async def test_missing_fields_handled(
        self,
        mock_retry_execute: AsyncMock,
        collector: RemoteOKCollector,
        query: CollectorQuery,
    ) -> None:
        minimal_job: dict[str, Any] = {
            "id": "min123",
            "title": "Minimal Job",
            "url": "https://remoteok.com/remote-jobs/min123",
            "company": "Startup Inc",
        }

        mock_retry_execute.return_value = _mock_response(
            json_data=_api_response([minimal_job]),
        )

        result = await collector.execute(query)

        assert result.success is True
        assert len(result.jobs) == 1
        assert result.jobs[0].title == "Minimal Job"
        assert result.jobs[0].company.name == "Startup Inc"
        assert result.jobs[0].location.remote_type == "remote"
        assert result.jobs[0].employment_type is None
        assert result.jobs[0].salary is None
        assert result.jobs[0].skills == []

    @patch("app.collectors.plugins.remoteok.collector.RetryStrategy.execute")
    async def test_jobs_without_id_skipped(
        self,
        mock_retry_execute: AsyncMock,
        collector: RemoteOKCollector,
        query: CollectorQuery,
    ) -> None:
        valid_job = _sample_job("abc123", title="Valid Job")
        no_id_job: dict[str, Any] = {
            "title": "No ID",
            "url": "https://remoteok.com/remote-jobs/no-id",
        }

        mock_retry_execute.return_value = _mock_response(
            json_data=_api_response([valid_job, no_id_job]),
        )

        result = await collector.execute(query)

        assert result.success is True
        assert len(result.jobs) == 1
        assert result.jobs[0].title == "Valid Job"

    @patch("app.collectors.plugins.remoteok.collector.RetryStrategy.execute")
    async def test_cleanup_releases_resources(
        self,
        mock_retry_execute: AsyncMock,
        collector: RemoteOKCollector,
        query: CollectorQuery,
    ) -> None:
        mock_retry_execute.return_value = _mock_response(json_data=[])

        await collector.execute(query)

        assert collector._client is None
        assert collector._initialized is False

    @patch("app.collectors.plugins.remoteok.collector.RetryStrategy.execute")
    async def test_cleanup_idempotent(
        self,
        mock_retry_execute: AsyncMock,
        collector: RemoteOKCollector,
        query: CollectorQuery,
    ) -> None:
        await collector.cleanup()
        await collector.cleanup()

    @patch("app.collectors.plugins.remoteok.collector.RetryStrategy.execute")
    async def test_normalize_with_empty_raw_data(
        self,
        mock_retry_execute: AsyncMock,
        collector: RemoteOKCollector,
        query: CollectorQuery,
    ) -> None:
        result = await collector.normalize({})
        assert result == []

        result = await collector.normalize({"jobs": []})
        assert result == []

        result = await collector.normalize(None)
        assert result == []

    @patch("app.collectors.plugins.remoteok.collector.RetryStrategy.execute")
    async def test_initialize_sets_up_client(
        self,
        mock_retry_execute: AsyncMock,
        collector: RemoteOKCollector,
    ) -> None:
        assert collector._client is None
        assert collector._initialized is False

        await collector.initialize()

        assert collector._client is not None
        assert collector._initialized is True
        await collector.cleanup()

    @patch("app.collectors.plugins.remoteok.collector.RetryStrategy.execute")
    async def test_timeout_handling(
        self,
        mock_retry_execute: AsyncMock,
        collector: RemoteOKCollector,
        query: CollectorQuery,
    ) -> None:
        from app.collectors.exceptions import NetworkError

        mock_retry_execute.side_effect = NetworkError(
            "Request to RemoteOK API timed out",
            source="remoteok",
        )

        result = await collector.execute(query)

        assert result.success is False
        assert len(result.errors) >= 1

    @patch("app.collectors.plugins.remoteok.collector.RetryStrategy.execute")
    async def test_registry_integration(
        self,
        mock_retry_execute: AsyncMock,
    ) -> None:
        from app.collectors.registry import CollectorRegistry

        cls = CollectorRegistry.get("remoteok")
        assert cls is not None
        assert cls is RemoteOKCollector

        names = CollectorRegistry.list_collectors()
        assert "remoteok" in names

    @patch("app.collectors.plugins.remoteok.collector.RetryStrategy.execute")
    async def test_collector_name_and_source_id(
        self,
        mock_retry_execute: AsyncMock,
        collector: RemoteOKCollector,
    ) -> None:
        assert collector.name == "remoteok"
        assert collector.source_id == "remoteok"

    @patch("app.collectors.plugins.remoteok.collector.RetryStrategy.execute")
    async def test_epoch_fallback_for_date(
        self,
        mock_retry_execute: AsyncMock,
        collector: RemoteOKCollector,
        query: CollectorQuery,
    ) -> None:
        job = _sample_job("abc123", title="Epoch Job")
        job["date"] = None
        job["epoch"] = 1736899200

        mock_retry_execute.return_value = _mock_response(
            json_data=_api_response([job]),
        )

        result = await collector.execute(query)

        assert result.success is True
        assert result.jobs[0].metadata.posted_at == datetime(
            2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc
        )

    def test_parse_location_various_formats(
        self,
        collector: RemoteOKCollector,
    ) -> None:
        loc = collector._parse_location("Worldwide")
        assert loc.remote_type == "remote"
        assert loc.country == "Worldwide"
        assert loc.city is None

        loc = collector._parse_location("United States")
        assert loc.remote_type == "remote"
        assert loc.country == "United States"

        loc = collector._parse_location("Remote - Europe")
        assert loc.remote_type == "remote"
        assert loc.country == "Europe"

        loc = collector._parse_location("San Francisco, CA")
        assert loc.remote_type == "remote"
        assert loc.city == "San Francisco"
        assert loc.state == "CA"

        loc = collector._parse_location("New York, NY, United States")
        assert loc.remote_type == "remote"
        assert loc.city == "New York"
        assert loc.state == "NY"
        assert loc.country == "United States"

        loc = collector._parse_location("")
        assert loc.remote_type == "remote"
        assert loc.city is None

    def test_parse_salary_various(
        self,
        collector: RemoteOKCollector,
    ) -> None:
        salary = collector._parse_salary(100000, 150000)
        assert salary is not None
        assert salary.min == 100000
        assert salary.max == 150000
        assert salary.currency == "USD"

        salary = collector._parse_salary(80000, None)
        assert salary is not None
        assert salary.min == 80000
        assert salary.max is None

        salary = collector._parse_salary(0, 0)
        assert salary is None

        salary = collector._parse_salary(None, None)
        assert salary is None

        salary = collector._parse_salary(0, 120000)
        assert salary is not None
        assert salary.min is None
        assert salary.max == 120000

    @patch("app.collectors.plugins.remoteok.collector.RetryStrategy.execute")
    async def test_unspecified_company_name(
        self,
        mock_retry_execute: AsyncMock,
        collector: RemoteOKCollector,
        query: CollectorQuery,
    ) -> None:
        job = _sample_job("abc123", title="Unknown Co")
        job["company"] = ""

        mock_retry_execute.return_value = _mock_response(
            json_data=_api_response([job]),
        )

        result = await collector.execute(query)

        assert result.success is True
        assert result.jobs[0].company.name == "Unknown"
