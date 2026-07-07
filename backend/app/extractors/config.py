from __future__ import annotations

from typing import Any

from app.core.settings import settings


class ExtractorConfigProvider:
    """Reads extractor configuration from the centralized settings layer.

    All extractor behavior is driven by values from the ``parsing``
    settings namespace. No values are hardcoded in extractor implementations.
    """

    @staticmethod
    def get_all() -> dict[str, Any]:
        return {
            "salary_default_currency": settings.parsing.salary_default_currency,
            "salary_default_interval": settings.parsing.salary_default_interval,
            "salary_local_formats_enabled": settings.parsing.salary_local_formats_enabled,
            "salary_normalize_to_yearly": settings.parsing.salary_normalize_to_yearly,
            "location_remote_keywords": settings.parsing.location_remote_keywords,
            "location_hybrid_keywords": settings.parsing.location_hybrid_keywords,
            "location_remote_suffixes": settings.parsing.location_remote_suffixes,
            "employment_synonyms": dict(settings.parsing.employment_synonyms),
            "experience_year_ranges": {
                k: list(v) for k, v in settings.parsing.experience_year_ranges.items()
            },
            "experience_level_keywords": {
                k: list(v) for k, v in settings.parsing.experience_level_keywords.items()
            },
            "title_seniority_prefixes": list(settings.parsing.title_seniority_prefixes),
            "title_stopwords": list(settings.parsing.title_stopwords),
            "metadata_date_formats": list(settings.parsing.metadata_date_formats),
            "metadata_default_categories": list(settings.parsing.metadata_default_categories),
        }

    @staticmethod
    def get_salary_config() -> dict[str, Any]:
        return {
            "default_currency": settings.parsing.salary_default_currency,
            "default_interval": settings.parsing.salary_default_interval,
            "local_formats_enabled": settings.parsing.salary_local_formats_enabled,
            "normalize_to_yearly": settings.parsing.salary_normalize_to_yearly,
        }

    @staticmethod
    def get_location_config() -> dict[str, Any]:
        return {
            "remote_keywords": list(settings.parsing.location_remote_keywords),
            "hybrid_keywords": list(settings.parsing.location_hybrid_keywords),
            "remote_suffixes": list(settings.parsing.location_remote_suffixes),
        }

    @staticmethod
    def get_employment_config() -> dict[str, Any]:
        return {
            "synonyms": dict(settings.parsing.employment_synonyms),
        }

    @staticmethod
    def get_experience_config() -> dict[str, Any]:
        return {
            "year_ranges": {
                k: list(v) for k, v in settings.parsing.experience_year_ranges.items()
            },
            "level_keywords": {
                k: list(v) for k, v in settings.parsing.experience_level_keywords.items()
            },
        }

    @staticmethod
    def get_title_config() -> dict[str, Any]:
        return {
            "seniority_prefixes": list(settings.parsing.title_seniority_prefixes),
            "stopwords": list(settings.parsing.title_stopwords),
        }

    @staticmethod
    def get_metadata_config() -> dict[str, Any]:
        return {
            "date_formats": list(settings.parsing.metadata_date_formats),
            "default_categories": list(settings.parsing.metadata_default_categories),
        }
