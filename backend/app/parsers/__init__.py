"""Parsing Rules Engine — reusable field-level parsers for job listings.

Every collector source (Greenhouse, Workday, Lever, Ashby, LinkedIn,
RemoteOK, etc.) feeds raw field values through this engine to produce
normalized, structured data models that downstream agents can consume
without re-implementing parsing logic.
"""

from app.parsers.base import BaseParser
from app.parsers.company_parser import CompanyParser
from app.parsers.employment_type_parser import EmploymentTypeParser
from app.parsers.experience_parser import ExperienceParser
from app.parsers.location_parser import LocationParser
from app.parsers.metadata_parser import MetadataParser
from app.parsers.registry import ParserRegistry
from app.parsers.salary_parser import SalaryParser
from app.parsers.title_parser import TitleParser

# Register all built-in parsers on import
ParserRegistry.register(SalaryParser)
ParserRegistry.register(LocationParser)
ParserRegistry.register(EmploymentTypeParser)
ParserRegistry.register(ExperienceParser)
ParserRegistry.register(CompanyParser)
ParserRegistry.register(TitleParser)
ParserRegistry.register(MetadataParser)

__all__ = [
    "BaseParser",
    "ParserRegistry",
    "SalaryParser",
    "LocationParser",
    "EmploymentTypeParser",
    "ExperienceParser",
    "CompanyParser",
    "TitleParser",
    "MetadataParser",
]
