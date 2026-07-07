from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

import httpx

from app.collectors.base import BaseCollector
from app.collectors.exceptions import NetworkError, ParsingError, StorageError
from app.collectors.models import (
    CollectorQuery,
    CollectorResult,
    CollectionStats,
    CompanyData,
    ErrorReport,
    JobData,
    JobMetadata,
    LocationData,
    SalaryData,
)
from app.collectors.registry import CollectorRegistry
from app.collectors.retry import RetryStrategy

GREENHOUSE_API_BASE = "https://api.greenhouse.io/v1/boards"


@CollectorRegistry.register
class GreenhouseCollector(BaseCollector):
    def __init__(
        self,
        config: Any,
        logger: Any = None,
    ) -> None:
        super().__init__(config, logger)
        self._client: Optional[httpx.AsyncClient] = None
        self._retry_strategy = RetryStrategy(
            max_retries=config.get("max_retries", 3),
            base_delay_seconds=1.0,
            max_delay_seconds=30.0,
            backoff_multiplier=config.get("retry_backoff_factor", 2.0),
            timeout_seconds=30.0,
        )

    @property
    def name(self) -> str:
        return "greenhouse"

    @property
    def source_id(self) -> str:
        return "greenhouse"

    async def initialize(self) -> None:
        headers = {
            "User-Agent": "AI-Career-Agent/1.0",
            "Accept": "application/json",
        }
        self._client = httpx.AsyncClient(
            headers=headers,
            timeout=httpx.Timeout(30.0),
        )
        self._initialized = True

    async def collect(self, query: CollectorQuery) -> CollectorResult:
        board_token = query.additional_filters.get(
            "board_token",
            query.additional_filters.get("company_name", "greenhouse"),
        )
        max_pages = self._config.get("max_pages_per_source", 5)
        all_jobs: list[dict[str, Any]] = []
        meta: dict[str, Any] = {}
        errors: list[ErrorReport] = []
        pages_collected = 0

        for page in range(1, max_pages + 1):
            url = f"{GREENHOUSE_API_BASE}/{board_token}/jobs?content=true&page={page}"
            try:
                response = await self._retry_strategy.execute(
                    self._fetch_page,
                    url,
                )
            except NetworkError as e:
                errors.append(
                    ErrorReport(
                        error_type="NetworkError",
                        error_message=str(e),
                        recoverable=True,
                    )
                )
                break
            except Exception as e:
                errors.append(
                    ErrorReport(
                        error_type=type(e).__name__,
                        error_message=str(e),
                        recoverable=False,
                    )
                )
                break

            data = response.json()
            page_jobs = data.get("jobs", [])
            if not page_jobs:
                break

            all_jobs.extend(page_jobs)
            pages_collected += 1
            meta = data.get("meta", {})

            if query.max_results and len(all_jobs) >= query.max_results:
                all_jobs = all_jobs[: query.max_results]
                break

            total = meta.get("total", 0)
            if len(all_jobs) >= total > 0:
                break

        raw_data = {"jobs": all_jobs, "meta": meta}

        return CollectorResult(
            source=self.source_id,
            query=query,
            raw_data=raw_data,
            existing_source_ids=[],
            stats=CollectionStats(
                total_discovered=len(all_jobs),
                pages_collected=pages_collected,
            ),
            errors=errors,
            success=len(errors) == 0,
        )

    async def _fetch_page(self, url: str) -> httpx.Response:
        if self._client is None:
            raise RuntimeError("Collector not initialized")
        try:
            response = await self._client.get(url)
        except httpx.TimeoutException as e:
            raise NetworkError(
                f"Request to {url} timed out",
                source=self.source_id,
                original=e,
            )
        except httpx.RequestError as e:
            raise NetworkError(
                f"Request to {url} failed: {e}",
                source=self.source_id,
                original=e,
            )

        if response.status_code == 429:
            from app.collectors.exceptions import RateLimitError

            retry_after = float(response.headers.get("Retry-After", "60"))
            raise RateLimitError(
                "Rate limited by Greenhouse API",
                retry_after=retry_after,
                source=self.source_id,
            )
        if response.status_code == 404:
            raise NetworkError(
                f"Greenhouse board '{url.split('/')[-3]}' not found (HTTP 404)",
                status_code=404,
                source=self.source_id,
            )
        if response.status_code != 200:
            raise NetworkError(
                f"Greenhouse API returned HTTP {response.status_code}",
                status_code=response.status_code,
                source=self.source_id,
            )

        try:
            response.json()
        except ValueError as e:
            raise ParsingError(
                "Invalid JSON response from Greenhouse API",
                source=self.source_id,
                original=e,
            )

        return response

    async def normalize(self, raw_data: Any) -> list[JobData]:
        jobs_raw = raw_data.get("jobs", []) if isinstance(raw_data, dict) else []
        board_token = "greenhouse"
        if isinstance(raw_data, dict):
            meta = raw_data.get("meta", {})
            board_token = meta.get("board_token", "")
            if not board_token and jobs_raw:
                board_token = jobs_raw[0].get("board_token", "greenhouse")
        normalized: list[JobData] = []
        for job in jobs_raw:
            try:
                job_data = self._normalize_single(job, board_token or "greenhouse")
                normalized.append(job_data)
            except Exception:
                continue
        return normalized

    def _normalize_single(
        self,
        job: dict[str, Any],
        board_token: str,
    ) -> JobData:
        source_job_id = str(job.get("id", ""))
        title = job.get("title", "")

        offices = job.get("offices", [])
        company_name = offices[0].get("name") if offices else board_token.title()

        location_raw = job.get("location", {})
        if isinstance(location_raw, dict):
            location_name = location_raw.get("name", "")
        else:
            location_name = str(location_raw) if location_raw else ""

        location = self._parse_location(location_name)

        company = CompanyData(name=company_name)

        metadata_list = job.get("metadata", [])
        employment_type = None
        experience_level = None
        salary_data = None
        for md in metadata_list:
            name = (md.get("name") or "").lower()
            value = md.get("value")
            if not value:
                continue
            if "employment" in name or "job type" in name:
                employment_type = str(value).lower()
            elif "experience" in name or "level" in name:
                experience_level = str(value).lower()
            elif "salary" in name:
                salary_data = self._parse_metadata_salary(str(value))
            elif "remote" in name:
                if str(value).lower() in ("remote", "yes", "true"):
                    location.remote_type = "remote"

        if offices and isinstance(offices[0], dict):
            office_location = offices[0].get("location", "")
            if office_location and not location.full_address:
                location.full_address = office_location

        posted_at_str = job.get("created_at")
        posted_at = None
        if posted_at_str:
            try:
                posted_at = datetime.fromisoformat(posted_at_str.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                posted_at = None

        content_html = job.get("content")
        content_text = None
        if content_html:
            import re

            content_text = re.sub(r"<[^>]+>", " ", content_html)
            content_text = re.sub(r"\s+", " ", content_text).strip()

        return JobData(
            title=title,
            company=company,
            location=location,
            salary=salary_data,
            metadata=JobMetadata(
                source=self.source_id,
                source_job_id=source_job_id,
                job_url=job.get("absolute_url", ""),
                apply_url=job.get("absolute_url", ""),
                posted_at=posted_at,
            ),
            description_raw=content_text,
            description_html=content_html,
            employment_type=employment_type,
            experience_level=experience_level,
            raw_data=job,
        )

    def _parse_location(self, location_name: str) -> LocationData:
        if not location_name:
            return LocationData(remote_type="onsite")

        name_lower = location_name.lower()
        is_remote = "remote" in name_lower or "anywhere" in name_lower

        parts = [p.strip() for p in location_name.split(",")]
        city = None
        state = None
        country = None
        full_address = location_name

        if is_remote:
            remote_type: str = "remote"
            if len(parts) >= 2:
                country = parts[-1].strip()
        else:
            remote_type = "onsite"
            if len(parts) == 3:
                city = parts[0]
                state = parts[1]
                country = parts[2]
            elif len(parts) == 2:
                city = parts[0]
                state_or_country = parts[1].strip()
                if len(state_or_country) <= 2:
                    state = state_or_country
                else:
                    country = state_or_country
            elif len(parts) == 1:
                city = parts[0]

        return LocationData(
            city=city,
            state=state,
            country=country,
            remote_type=remote_type,
            full_address=full_address,
        )

    def _parse_metadata_salary(self, value: str) -> Optional[SalaryData]:
        import re

        numbers = re.findall(r"\d[\d,]*", value)
        cleaned = []
        for n in numbers:
            try:
                cleaned.append(int(n.replace(",", "")))
            except ValueError:
                continue
        if not cleaned:
            return None
        return SalaryData(
            min=cleaned[0],
            max=cleaned[-1] if len(cleaned) > 1 else None,
            currency="USD",
            interval="yearly",
        )

    async def validate(self, jobs: list[JobData]) -> list[JobData]:
        valid: list[JobData] = []
        for job in jobs:
            if not job.title:
                continue
            if not job.metadata.source_job_id:
                continue
            if not job.metadata.job_url:
                continue
            valid.append(job)
        return valid

    async def deduplicate(
        self,
        jobs: list[JobData],
        existing_source_ids: list[str],
    ) -> list[JobData]:
        existing_set = set(existing_source_ids)
        return [j for j in jobs if j.metadata.source_job_id not in existing_set]

    async def save(self, jobs: list[JobData]) -> CollectorResult:
        if not hasattr(self, "_execute_query") or not hasattr(self, "_execute_stats"):
            return CollectorResult(
                source=self.source_id,
                query=CollectorQuery(),
                jobs=jobs,
                stats=CollectionStats(total_saved=len(jobs)),
                success=True,
            )

        from app.db.repositories import JobRepository
        from app.db.session import get_session

        saved_count = 0
        failed_count = 0
        errors: list[ErrorReport] = []

        try:
            async with get_session() as session:
                repo = JobRepository(session)
                for job in jobs:
                    try:
                        await repo.save_job(job)
                        saved_count += 1
                    except Exception as e:
                        failed_count += 1
                        errors.append(
                            ErrorReport(
                                error_type=type(e).__name__,
                                error_message=str(e),
                                recoverable=False,
                            )
                        )
        except Exception as e:
            return CollectorResult(
                source=self.source_id,
                query=self._execute_query,
                jobs=jobs,
                stats=CollectionStats(
                    total_discovered=self._execute_stats.get(
                        "total_discovered", 0
                    ),
                    total_saved=0,
                    total_failed=len(jobs),
                ),
                errors=[
                    ErrorReport(
                        error_type=type(e).__name__,
                        error_message=f"Database connection failed: {e}",
                        recoverable=True,
                    )
                ],
                success=False,
            )

        stats = CollectionStats(
            total_discovered=self._execute_stats.get("total_discovered", 0),
            total_normalized=self._execute_stats.get("total_normalized", 0),
            total_valid=self._execute_stats.get("total_valid", 0),
            total_duplicates_removed=self._execute_stats.get(
                "total_duplicates", 0
            ),
            total_saved=saved_count,
            total_failed=failed_count,
            pages_collected=self._execute_stats.get("pages_collected", 0),
        )

        return CollectorResult(
            source=self.source_id,
            query=self._execute_query,
            jobs=jobs,
            stats=stats,
            errors=errors,
            success=failed_count == 0,
        )

    async def execute(self, query: CollectorQuery) -> CollectorResult:
        self._execute_query = query
        try:
            await self.initialize()
            raw_result = await self.collect(query)

            total_discovered = raw_result.stats.total_discovered
            pages_collected = raw_result.stats.pages_collected
            existing_ids = raw_result.existing_source_ids
            collect_errors = raw_result.errors

            if not raw_result.success or collect_errors:
                await self.cleanup()
                return CollectorResult(
                    source=self.source_id,
                    query=query,
                    jobs=[],
                    stats=CollectionStats(
                        total_discovered=total_discovered,
                        pages_collected=pages_collected,
                    ),
                    errors=collect_errors,
                    success=False,
                )

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

    async def cleanup(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        self._initialized = False
