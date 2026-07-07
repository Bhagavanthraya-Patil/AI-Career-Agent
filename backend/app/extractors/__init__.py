"""Job Details Extractor & Model Mapping layer.

Extractors consume raw collector payloads (Greenhouse, Lever, Ashby, Workday,
RemoteOK, or any future source) and produce canonical ``JobData`` models by
reusing the existing Parsing Rules Engine (``app.parsers``) for field-level
normalization.
"""

from app.extractors.base import BaseExtractor
from app.extractors.extractor_registry import ExtractorRegistry
from app.extractors.field_mapper import FieldMapper
from app.extractors.html_cleaner import HtmlCleaner
from app.extractors.description_extractor import DescriptionExtractor
from app.extractors.salary_extractor import SalaryExtractor
from app.extractors.location_extractor import LocationExtractor
from app.extractors.metadata_extractor import MetadataExtractor
from app.extractors.job_extractor import JobExtractor
from app.extractors.config import ExtractorConfigProvider

ExtractorRegistry.register(SalaryExtractor)
ExtractorRegistry.register(LocationExtractor)
ExtractorRegistry.register(DescriptionExtractor)
ExtractorRegistry.register(MetadataExtractor)

__all__ = [
    "BaseExtractor",
    "ExtractorRegistry",
    "FieldMapper",
    "HtmlCleaner",
    "DescriptionExtractor",
    "SalaryExtractor",
    "LocationExtractor",
    "MetadataExtractor",
    "JobExtractor",
    "ExtractorConfigProvider",
]
