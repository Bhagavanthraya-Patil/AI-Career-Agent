from __future__ import annotations

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

LEVER_API_BASE = "https://api.lever.co/v0/postings"


@CollectorRegistry.register
class LeverCollector(BaseCollector):
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
        return "lever"

    @property
    def source_id(self) -> str:
        return "lever"

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

    def _get_board_token(self, query: CollectorQuery) -> str:
        token = query.additional_filters.get("board_token", "")
        if not token:
            token = query.additional_filters.get("company_name", "")
        if not token:
            token = "default"
        return token

    async def collect(self, query: CollectorQuery) -> CollectorResult:
        board_token = self._get_board_token(query)
        max_pages = self._config.get("max_pages_per_source", 5)
        limit = self._config.get("limit", 100)
        all_jobs: list[dict[str, Any]] = []
        errors: list[ErrorReport] = []
        pages_collected = 0

        for page in range(max_pages):
            offset = page * limit
            url = f"{LEVER_API_BASE}/{board_token}?limit={limit}&offset={offset}"

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

            try:
                page_data = response.json()
            except ValueError:
                errors.append(
                    ErrorReport(
                        error_type="ParsingError",
                        error_message="Invalid JSON from Lever API",
                        recoverable=False,
                    )
                )
                break

            if not isinstance(page_data, list):
                errors.append(
                    ErrorReport(
                        error_type="ParsingError",
                        error_message="Unexpected response format from Lever API",
                        recoverable=False,
                    )
                )
                break

            if not page_data:
                break

            all_jobs.extend(page_data)
            pages_collected += 1

            if query.max_results and len(all_jobs) >= query.max_results:
                all_jobs = all_jobs[: query.max_results]
                break

            if len(page_data) < limit:
                break

        raw_data = {"postings": all_jobs, "board_token": board_token}

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
                f"Request to Lever API timed out",
                source=self.source_id,
                original=e,
            )
        except httpx.RequestError as e:
            raise NetworkError(
                f"Request to Lever API failed: {e}",
                source=self.source_id,
                original=e,
            )

        if response.status_code == 429:
            from app.collectors.exceptions import RateLimitError

            retry_after = float(response.headers.get("Retry-After", "60"))
            raise RateLimitError(
                "Rate limited by Lever API",
                retry_after=retry_after,
                source=self.source_id,
            )
        if response.status_code == 404:
            raise NetworkError(
                f"Lever board '{url.split('/')[-1].split('?')[0]}' not found (HTTP 404)",
                status_code=404,
                source=self.source_id,
            )
        if response.status_code != 200:
            raise NetworkError(
                f"Lever API returned HTTP {response.status_code}",
                status_code=response.status_code,
                source=self.source_id,
            )

        try:
            response.json()
        except ValueError as e:
            raise ParsingError(
                "Invalid JSON response from Lever API",
                source=self.source_id,
                original=e,
            )

        return response

    async def normalize(self, raw_data: Any) -> list[JobData]:
        postings = (
            raw_data.get("postings", [])
            if isinstance(raw_data, dict)
            else []
        )
        board_token = "default"
        if isinstance(raw_data, dict):
            board_token = raw_data.get("board_token", "default")

        normalized: list[JobData] = []
        for posting in postings:
            try:
                job_data = self._normalize_single(posting, board_token)
                normalized.append(job_data)
            except Exception:
                continue
        return normalized

    def _normalize_single(
        self,
        posting: dict[str, Any],
        board_token: str,
    ) -> JobData:
        title = posting.get("text", "")

        categories = posting.get("categories") or {}
        location_str = categories.get("location", "") or ""

        location = self._parse_location(location_str)

        team = categories.get("team", "")
        company_name = board_token.title()
        if team:
            company_name = team

        company = CompanyData(name=company_name)

        source_job_id = str(posting.get("id", ""))
        hosted_url = posting.get("hostedUrl", "")
        job_url = hosted_url if hosted_url else ""

        commitment = categories.get("commitment", "")
        employment_type = None
        if commitment:
            employment_type = commitment.lower()

        created_at_ms = posting.get("createdAt")
        posted_at = None
        if created_at_ms is not None:
            try:
                posted_at = datetime.fromtimestamp(
                    created_at_ms / 1000.0, tz=timezone.utc
                )
            except (ValueError, TypeError, OSError):
                posted_at = None

        description_html = posting.get("description", "") or ""
        description_plain = posting.get("descriptionPlain", "") or ""

        lists = posting.get("lists") or []
        for lst in lists:
            list_content = lst.get("content", "") or ""
            if list_content:
                description_html += "\n" + list_content

        description_text = description_plain
        if not description_text and description_html:
            description_text = re.sub(r"<[^>]+>", " ", description_html)
            description_text = re.sub(r"\s+", " ", description_text).strip()

        additional = posting.get("additional", "") or ""
        salary = self._parse_additional_salary(additional)

        return JobData(
            title=title,
            company=company,
            location=location,
            salary=salary,
            metadata=JobMetadata(
                source=self.source_id,
                source_job_id=source_job_id,
                job_url=job_url,
                apply_url=job_url,
                posted_at=posted_at,
            ),
            description_raw=description_text or None,
            description_html=description_html or None,
            employment_type=employment_type,
            raw_data=posting,
        )

    def _parse_location(self, location_str: str) -> LocationData:
        if not location_str:
            return LocationData(remote_type="onsite")

        name_lower = location_str.lower()
        is_remote = "remote" in name_lower or "anywhere" in name_lower

        parts = [p.strip() for p in location_str.split(",")]
        city = None
        state = None
        country = None

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
            full_address=location_str,
        )

    def _parse_additional_salary(self, additional: str) -> Optional[SalaryData]:
        if not additional:
            return None
        numbers = re.findall(r"\d[\d,]*", additional)
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
