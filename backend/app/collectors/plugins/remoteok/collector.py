from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from app.collectors.base import BaseCollector
from app.collectors.exceptions import NetworkError, ParsingError
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

REMOTEOK_API_BASE = "https://remoteok.com/api"

EMPLOYMENT_TYPE_KEYWORDS: dict[str, str] = {
    "full-time": "full-time",
    "full time": "full-time",
    "part-time": "part-time",
    "part time": "part-time",
    "contract": "contract",
    "freelance": "contract",
    "internship": "internship",
    "temporary": "contract",
}


@CollectorRegistry.register
class RemoteOKCollector(BaseCollector):
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
        return "remoteok"

    @property
    def source_id(self) -> str:
        return "remoteok"

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
        url = REMOTEOK_API_BASE
        all_jobs: list[dict[str, Any]] = []
        errors: list[ErrorReport] = []
        pages_collected = 0

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
            return self._build_result(query, all_jobs, errors, pages_collected)
        except Exception as e:
            errors.append(
                ErrorReport(
                    error_type=type(e).__name__,
                    error_message=str(e),
                    recoverable=False,
                )
            )
            return self._build_result(query, all_jobs, errors, pages_collected)

        try:
            data = response.json()
        except ValueError:
            errors.append(
                ErrorReport(
                    error_type="ParsingError",
                    error_message="Invalid JSON from RemoteOK API",
                    recoverable=False,
                )
            )
            return self._build_result(query, all_jobs, errors, pages_collected)

        if not isinstance(data, list):
            errors.append(
                ErrorReport(
                    error_type="ParsingError",
                    error_message="Unexpected response format from RemoteOK API",
                    recoverable=False,
                )
            )
            return self._build_result(query, all_jobs, errors, pages_collected)

        if not data:
            return self._build_result(query, all_jobs, errors, pages_collected)

        for item in data:
            if not isinstance(item, dict):
                continue
            if not item.get("id"):
                continue
            all_jobs.append(item)

        pages_collected = 1

        if query.max_results and len(all_jobs) > query.max_results:
            all_jobs = all_jobs[: query.max_results]

        return self._build_result(query, all_jobs, errors, pages_collected)

    def _build_result(
        self,
        query: CollectorQuery,
        all_jobs: list[dict[str, Any]],
        errors: list[ErrorReport],
        pages_collected: int,
    ) -> CollectorResult:
        raw_data = {"jobs": all_jobs}
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
                "Request to RemoteOK API timed out",
                source=self.source_id,
                original=e,
            )
        except httpx.RequestError as e:
            raise NetworkError(
                f"Request to RemoteOK API failed: {e}",
                source=self.source_id,
                original=e,
            )

        if response.status_code == 429:
            from app.collectors.exceptions import RateLimitError

            retry_after = float(response.headers.get("Retry-After", "60"))
            raise RateLimitError(
                "Rate limited by RemoteOK API",
                retry_after=retry_after,
                source=self.source_id,
            )
        if response.status_code != 200:
            raise NetworkError(
                f"RemoteOK API returned HTTP {response.status_code}",
                status_code=response.status_code,
                source=self.source_id,
            )

        try:
            response.json()
        except ValueError as e:
            raise ParsingError(
                "Invalid JSON response from RemoteOK API",
                source=self.source_id,
                original=e,
            )

        return response

    async def normalize(self, raw_data: Any) -> list[JobData]:
        jobs_raw = raw_data.get("jobs", []) if isinstance(raw_data, dict) else []
        normalized: list[JobData] = []
        for job in jobs_raw:
            try:
                job_data = self._normalize_single(job)
                normalized.append(job_data)
            except Exception:
                continue
        return normalized

    def _normalize_single(self, job: dict[str, Any]) -> JobData:
        source_job_id = str(job.get("id", ""))
        title = job.get("title", "")

        company_name = job.get("company", "")
        company_logo = job.get("company_logo") or None
        company = CompanyData(name=company_name or "Unknown", logo_url=company_logo)

        location_str = job.get("location", "") or ""
        location = self._parse_location(location_str)

        salary = self._parse_salary(job.get("salary_min"), job.get("salary_max"))

        tags_raw = job.get("tags", "")
        skills: list[str] = []
        employment_type: Optional[str] = None
        if tags_raw:
            try:
                tags = (
                    json.loads(tags_raw)
                    if isinstance(tags_raw, str)
                    else (tags_raw if isinstance(tags_raw, list) else [])
                )
                if isinstance(tags, list):
                    for tag in tags:
                        tag_lower = str(tag).lower().strip()
                        if tag_lower:
                            skills.append(tag_lower)
                            for keyword, etype in EMPLOYMENT_TYPE_KEYWORDS.items():
                                if keyword == tag_lower:
                                    employment_type = etype
            except (json.JSONDecodeError, TypeError):
                pass

        posted_at = None
        date_raw = job.get("date") or job.get("created_at")
        if date_raw:
            try:
                posted_at = datetime.fromisoformat(
                    str(date_raw).replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass

        if posted_at is None:
            epoch_raw = job.get("epoch")
            if epoch_raw:
                try:
                    posted_at = datetime.fromtimestamp(
                        int(epoch_raw), tz=timezone.utc
                    )
                except (ValueError, TypeError, OSError):
                    posted_at = None

        job_url = job.get("url", "")
        apply_url = job.get("apply_url", "")

        description_html = job.get("description", "") or ""

        description_text = None
        if description_html:
            description_text = re.sub(r"<[^>]+>", " ", description_html)
            description_text = re.sub(r"\s+", " ", description_text).strip()

        return JobData(
            title=title,
            company=company,
            location=location,
            salary=salary,
            metadata=JobMetadata(
                source=self.source_id,
                source_job_id=source_job_id,
                job_url=job_url,
                apply_url=apply_url or job_url,
                posted_at=posted_at,
            ),
            description_raw=description_text,
            description_html=description_html,
            employment_type=employment_type,
            skills=skills,
            raw_data=job,
        )

    def _parse_location(self, location_str: str) -> LocationData:
        if not location_str:
            return LocationData(remote_type="remote")

        name_lower = location_str.lower()
        is_remote = "remote" in name_lower or "anywhere" in name_lower

        parts = [p.strip() for p in location_str.split(",")]
        city = None
        state = None
        country = None

        if is_remote:
            remote_type: str = "remote"
            if " - " in location_str:
                country = location_str.split(" - ")[-1].strip()
            elif len(parts) >= 2:
                country = parts[-1].strip()
        else:
            remote_type = "remote"
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
                country_or_city = parts[0]
                if len(country_or_city) > 2 or country_or_city.lower() in (
                    "worldwide",
                    "global",
                    "international",
                ):
                    country = country_or_city
                else:
                    city = country_or_city

        return LocationData(
            city=city,
            state=state,
            country=country,
            remote_type=remote_type,
            full_address=location_str,
        )

    def _parse_salary(
        self,
        salary_min: Any,
        salary_max: Any,
    ) -> Optional[SalaryData]:
        min_val: Optional[int] = None
        max_val: Optional[int] = None

        if salary_min is not None:
            try:
                val = int(salary_min)
                if val > 0:
                    min_val = val
            except (ValueError, TypeError):
                pass

        if salary_max is not None:
            try:
                val = int(salary_max)
                if val > 0:
                    max_val = val
            except (ValueError, TypeError):
                pass

        if min_val is None and max_val is None:
            return None

        return SalaryData(
            min=min_val,
            max=max_val,
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
