from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from app.collectors.exceptions import ValidationError
from app.collectors.models import CompanyData, JobData, JobMetadata, LocationData, SalaryData
from app.collectors.logging import CollectorLoggerProtocol
from app.extractors.description_extractor import DescriptionExtractor
from app.extractors.extractor_registry import ExtractorRegistry
from app.extractors.field_mapper import FieldMapper
from app.extractors.location_extractor import LocationExtractor
from app.extractors.metadata_extractor import MetadataExtractor
from app.extractors.salary_extractor import SalaryExtractor
from app.parsers import ParserRegistry


class JobExtractor:
    """Top-level orchestrator for the extractor layer.

    Accepts a raw collector payload (``dict``) and a source name,
    and produces a canonical ``JobData`` model by chaining:
      1. ``FieldMapper`` — translates source-specific fields to canonical keys
      2. Individual ``BaseExtractor`` instances — normalize each field group
      3. Assembly into the final ``JobData`` model

    Usage::

        extractor = JobExtractor()
        job = extractor.extract(raw_job_dict, source="greenhouse")
    """

    def __init__(
        self,
        config: Optional[dict[str, Any]] = None,
        logger: Optional[CollectorLoggerProtocol] = None,
    ) -> None:
        self._config = config or {}
        self._logger = logger
        self._field_mapper = FieldMapper()
        self._salary_extractor = SalaryExtractor(
            config=self._config,
            logger=self._logger,
        )
        self._location_extractor = LocationExtractor(
            config=self._config,
            logger=self._logger,
        )
        self._description_extractor = DescriptionExtractor(
            config=self._config,
            logger=self._logger,
        )
        self._metadata_extractor = MetadataExtractor(
            config=self._config,
            logger=self._logger,
        )

    def extract(
        self,
        raw_data: dict[str, Any],
        source: str,
        validate: bool = True,
    ) -> JobData:
        """Convert a raw collector payload into a canonical ``JobData``.

        Args:
            raw_data: Raw job dict from a collector.
            source: Source platform name (greenhouse, lever, ashby, etc.).
            validate: If True, raise ``ValidationError`` for invalid data.

        Returns:
            A fully normalized ``JobData`` model.

        Raises:
            ValidationError: If required fields are missing and validate=True.
        """
        canonical = self._field_mapper.map(raw_data, source)

        meta_dict = self._metadata_extractor.extract(canonical)
        job_metadata = self._metadata_extractor.build_job_metadata(meta_dict)
        company = self._metadata_extractor.build_company_data(meta_dict)

        location = self._location_extractor.extract(canonical)
        salary = self._salary_extractor.extract(canonical)
        desc_raw, desc_html = self._description_extractor.extract(canonical)

        title = str(canonical.get("title", "")).strip()

        skills = meta_dict.get("skills", [])
        department = meta_dict.get("department")

        if department and isinstance(department, str) and department.strip():
            if department.lower() not in [s.lower() for s in skills]:
                skills = [*skills, department]

        employment_type = self._normalize_employment_type(meta_dict.get("employment_type"))
        experience_level = meta_dict.get("experience_level")

        if validate:
            if not title:
                raise ValidationError(
                    message="Job title is required",
                    field="title",
                    value=title,
                    source=source,
                )
            if not job_metadata.source_job_id:
                raise ValidationError(
                    message="Source job ID is required",
                    field="source_job_id",
                    value=job_metadata.source_job_id,
                    source=source,
                )

        raw_for_storage = canonical.get("raw_data", raw_data)

        return JobData(
            title=title,
            company=company,
            location=location,
            salary=salary,
            metadata=job_metadata,
            description_raw=desc_raw,
            description_html=desc_html,
            employment_type=employment_type,
            experience_level=experience_level,
            skills=skills,
            raw_data=raw_for_storage,
        )

    def _normalize_employment_type(self, raw: Any) -> Optional[str]:
        if not raw or not isinstance(raw, str) or not raw.strip():
            return None
        parser = ParserRegistry.get_or_create("employment_type")
        if parser is None:
            return raw.strip().lower()
        result = parser.parse(raw)
        return result.normalized

    def extract_batch(
        self,
        raw_items: list[dict[str, Any]],
        source: str,
        validate: bool = True,
    ) -> list[JobData]:
        """Convert a batch of raw payloads into ``JobData`` models.

        Invalid items are skipped (logged) rather than failing the batch.
        """
        results: list[JobData] = []
        for item in raw_items:
            try:
                job = self.extract(item, source=source, validate=validate)
                results.append(job)
            except ValidationError:
                if self._logger:
                    self._logger.warning(
                        "Skipping invalid job during batch extraction",
                        source=source,
                    )
                continue
        return results
