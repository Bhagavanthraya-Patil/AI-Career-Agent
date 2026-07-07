from __future__ import annotations

import re
from datetime import datetime
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

WORKDAY_API_TEMPLATE = "https://{tenant}.myworkdayjobs.com/wday/cxs/{tenant}/{careerSite}/jobs"


@CollectorRegistry.register
class WorkdayCollector(BaseCollector):
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
        return "workday"

    @property
    def source_id(self) -> str:
        return "workday"

    async def initialize(self) -> None:
        headers = {
            "User-Agent": "AI-Career-Agent/1.0",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        self._client = httpx.AsyncClient(
            headers=headers,
            timeout=httpx.Timeout(30.0),
        )
        self._initialized = True

    def _get_tenant_and_site(self, query: CollectorQuery) -> tuple[str, str]:
        tenant = query.additional_filters.get("tenant", "")
        if not tenant:
            tenant = query.additional_filters.get("company_name", "")
        if not tenant:
            tenant = "default"
        career_site = query.additional_filters.get("career_site", tenant)
        return tenant, career_site

    async def collect(self, query: CollectorQuery) -> CollectorResult:
        tenant, career_site = self._get_tenant_and_site(query)
        url = WORKDAY_API_TEMPLATE.format(
            tenant=tenant,
            careerSite=career_site,
        )
        max_pages = self._config.get("max_pages_per_source", 5)
        limit = 20
        all_jobs: list[dict[str, Any]] = []
        errors: list[ErrorReport] = []
        pages_collected = 0
        total_count = 0

        for page in range(max_pages):
            offset = page * limit
            body: dict[str, Any] = {
                "limit": limit,
                "offset": offset,
                "searchText": "",
            }
            if query.keywords:
                body["searchText"] = " ".join(query.keywords)

            try:
                response = await self._retry_strategy.execute(
                    self._fetch_page,
                    url,
                    body,
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

            try:
                data = response.json()
            except ValueError:
                errors.append(
                    ErrorReport(
                        error_type="ParsingError",
                        error_message="Invalid JSON in Workday API response",
                        recoverable=False,
                    )
                )
                break

            page_jobs = data.get("jobPostings", [])
            total_count = data.get("total", 0)

            if not page_jobs:
                break

            all_jobs.extend(page_jobs)
            pages_collected += 1

            if query.max_results and len(all_jobs) >= query.max_results:
                all_jobs = all_jobs[: query.max_results]
                break

            if total_count > 0 and len(all_jobs) >= total_count:
                break

        raw_data = {
            "jobPostings": all_jobs,
            "total": total_count,
            "tenant": tenant,
            "career_site": career_site,
        }

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

    async def _fetch_page(
        self,
        url: str,
        body: dict[str, Any],
    ) -> httpx.Response:
        if self._client is None:
            raise RuntimeError("Collector not initialized")
        try:
            response = await self._client.post(url, json=body)
        except httpx.TimeoutException as e:
            raise NetworkError(
                f"Request to Workday API timed out",
                source=self.source_id,
                original=e,
            )
        except httpx.RequestError as e:
            raise NetworkError(
                f"Request to Workday API failed: {e}",
                source=self.source_id,
                original=e,
            )

        if response.status_code == 429:
            from app.collectors.exceptions import RateLimitError

            retry_after = float(response.headers.get("Retry-After", "60"))
            raise RateLimitError(
                "Rate limited by Workday API",
                retry_after=retry_after,
                source=self.source_id,
            )
        if response.status_code == 403:
            raise NetworkError(
                "Workday API returned HTTP 403 (Forbidden)",
                status_code=403,
                source=self.source_id,
            )
        if response.status_code != 200:
            raise NetworkError(
                f"Workday API returned HTTP {response.status_code}",
                status_code=response.status_code,
                source=self.source_id,
            )

        try:
            response.json()
        except ValueError as e:
            raise ParsingError(
                "Invalid JSON response from Workday API",
                source=self.source_id,
                original=e,
            )

        return response

    async def normalize(self, raw_data: Any) -> list[JobData]:
        job_postings = (
            raw_data.get("jobPostings", [])
            if isinstance(raw_data, dict)
            else []
        )
        tenant = "default"
        if isinstance(raw_data, dict):
            tenant = raw_data.get("tenant", "default")

        normalized: list[JobData] = []
        for posting in job_postings:
            try:
                job_data = self._normalize_single(posting, tenant)
                normalized.append(job_data)
            except Exception:
                continue
        return normalized

    def _normalize_single(
        self,
        posting: dict[str, Any],
        tenant: str,
    ) -> JobData:
        title = posting.get("title", "")

        location_str = posting.get("location", "") or ""
        location = self._parse_location(location_str)

        company_name = posting.get("company", "")
        if not company_name:
            company_name = tenant.title()

        company = CompanyData(name=company_name)

        source_job_id = self._extract_job_id(posting)
        external_path = posting.get("externalPath", "")
        job_url = ""
        if external_path:
            job_url = f"https://{tenant}.myworkdayjobs.com{external_path}"

        posted_at = None
        posted_on = posting.get("postedOn")
        if posted_on:
            try:
                posted_at = datetime.fromisoformat(
                    posted_on.replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                posted_at = None

        bullet_fields = posting.get("bulletFields", [])
        employment_type = None
        experience_level = None
        remote_type_override: Optional[str] = None
        for field in bullet_fields:
            f_lower = str(field).lower()
            if any(t in f_lower for t in ("full-time", "part-time", "contract", "temporary", "internship")):
                employment_type = f_lower
            elif any(t in f_lower for t in ("entry", "mid", "senior", "lead", "principal", "junior")):
                experience_level = self._map_experience_level(f_lower)
            elif "remote" in f_lower:
                remote_type_override = "remote"
            elif "hybrid" in f_lower:
                remote_type_override = "hybrid"

        if remote_type_override:
            location.remote_type = remote_type_override

        job_posting_info = posting.get("jobPostingInfo", {}) or {}
        description_html = job_posting_info.get("jobDescription", "")

        description_text = None
        if description_html:
            description_text = re.sub(r"<[^>]+>", " ", description_html)
            description_text = re.sub(r"\s+", " ", description_text).strip()

        return JobData(
            title=title,
            company=company,
            location=location,
            metadata=JobMetadata(
                source=self.source_id,
                source_job_id=source_job_id,
                job_url=job_url,
                apply_url=job_url,
                posted_at=posted_at,
            ),
            description_raw=description_text,
            description_html=description_html,
            employment_type=employment_type,
            experience_level=experience_level,
            raw_data=posting,
        )

    def _extract_job_id(self, posting: dict[str, Any]) -> str:
        external_path = posting.get("externalPath", "")
        if external_path:
            match = re.search(r"_(\w+)$", external_path)
            if match:
                return match.group(1)
        return posting.get("jobPostingId", str(posting.get("title", "")))

    def _map_experience_level(self, field: str) -> str:
        mapping = {
            "entry": "entry",
            "junior": "entry",
            "mid": "mid",
            "senior": "senior",
            "lead": "lead",
            "principal": "lead",
            "director": "lead",
            "manager": "mid",
        }
        for key, val in mapping.items():
            if key in field:
                return val
        return "mid"

    def _parse_location(self, location_str: str) -> LocationData:
        if not location_str:
            return LocationData(remote_type="onsite")

        name_lower = location_str.lower()
        is_remote = "remote" in name_lower or "anywhere" in name_lower
        is_hybrid = "hybrid" in name_lower

        parts = [p.strip() for p in location_str.split(",")]
        city = None
        state = None
        country = None
        full_address = location_str

        if is_hybrid:
            remote_type: str = "hybrid"
            if len(parts) >= 2:
                city = parts[-2].strip()
                country = parts[-1].strip()
        elif is_remote:
            remote_type = "remote"
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
