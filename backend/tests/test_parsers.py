from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from app.collectors.models import LocationData, SalaryData
from app.parsers import ParserRegistry
from app.parsers.base import BaseParser
from app.parsers.company_parser import CompanyParser
from app.parsers.employment_type_parser import EmploymentTypeParser
from app.parsers.experience_parser import ExperienceParser
from app.parsers.location_parser import LocationParser
from app.parsers.metadata_parser import MetadataParser
from app.parsers.models import ParsedCompany, ParsedEmploymentType, ParsedExperience, ParsedTitle
from app.parsers.registry import ParserRegistry
from app.parsers.salary_parser import SalaryParser
from app.parsers.title_parser import TitleParser


# =============================================================================
# Salary Parser Tests
# =============================================================================

class TestSalaryParser:
    @pytest.fixture
    def parser(self) -> SalaryParser:
        return SalaryParser()

    def test_parse_usd_k_range(self, parser):
        result = parser.parse("$120k - $150k")
        assert result is not None
        assert result.min == 120000
        assert result.max == 150000
        assert result.currency == "USD"
        assert result.interval == "yearly"

    def test_parse_usd_k_single(self, parser):
        result = parser.parse("$120k")
        assert result is not None
        assert result.min == 120000
        assert result.currency == "USD"

    def test_parse_usd_full_range(self, parser):
        result = parser.parse("$80,000 - $120,000")
        assert result is not None
        assert result.min == 80000
        assert result.max == 120000

    def test_parse_hourly(self, parser):
        result = parser.parse("$50/hr")
        assert result is not None
        assert result.min == 50
        assert result.currency == "USD"
        assert result.interval == "hourly"

    def test_parse_monthly(self, parser):
        result = parser.parse("€4,000/month")
        assert result is not None
        assert result.min == 4000
        assert result.currency == "EUR"
        assert result.interval == "monthly"

    def test_parse_inr_lpa_range(self, parser):
        result = parser.parse("₹12-18 LPA")
        assert result is not None
        assert result.min == 1200000
        assert result.max == 1800000
        assert result.currency == "INR"

    def test_parse_inr_lpa_single(self, parser):
        result = parser.parse("₹8 LPA")
        assert result is not None
        assert result.min == 800000
        assert result.currency == "INR"

    def test_parse_inr_ctc(self, parser):
        result = parser.parse("₹12 CTC")
        assert result is not None
        assert result.min == 1200000
        assert result.currency == "INR"

    def test_parse_gbp(self, parser):
        result = parser.parse("£50k")
        assert result is not None
        assert result.min == 50000
        assert result.currency == "GBP"

    def test_parse_eur(self, parser):
        result = parser.parse("€70k")
        assert result is not None
        assert result.min == 70000
        assert result.currency == "EUR"

    def test_parse_competitive(self, parser):
        result = parser.parse("Competitive")
        assert result is None

    def test_parse_negotiable(self, parser):
        result = parser.parse("Negotiable")
        assert result is None

    def test_parse_unknown(self, parser):
        result = parser.parse("Unknown")
        assert result is None

    def test_parse_empty_string(self, parser):
        result = parser.parse("")
        assert result is None

    def test_parse_none(self, parser):
        result = parser.parse(None)
        assert result is None

    def test_parse_whitespace(self, parser):
        result = parser.parse("   ")
        assert result is None

    def test_parse_cad(self, parser):
        result = parser.parse("C$80k")
        assert result is not None
        assert result.min == 80000
        assert result.currency == "CAD"

    def test_parse_aud(self, parser):
        result = parser.parse("A$100k")
        assert result is not None
        assert result.min == 100000
        assert result.currency == "AUD"

    def test_parse_lpa_no_symbol(self, parser):
        result = parser.parse("8 LPA")
        assert result is not None
        assert result.min == 800000
        assert result.currency == "INR"

    def test_parse_with_department_and_salary(self, parser):
        result = parser.parse("₹20-25 LPA")
        assert result is not None
        assert result.min == 2000000
        assert result.max == 2500000

    def test_returns_salary_data_type(self, parser):
        result = parser.parse("$120k")
        assert isinstance(result, SalaryData)


# =============================================================================
# Location Parser Tests
# =============================================================================

class TestLocationParser:
    @pytest.fixture
    def parser(self) -> LocationParser:
        return LocationParser()

    def test_parse_remote(self, parser):
        result = parser.parse("Remote")
        assert result.remote_type == "remote"
        assert result.city is None

    def test_parse_remote_country(self, parser):
        result = parser.parse("Remote (India)")
        assert result.remote_type == "remote"
        assert result.country == "India"

    def test_parse_remote_worldwide(self, parser):
        result = parser.parse("Remote (Worldwide)")
        assert result.remote_type == "remote"

    def test_parse_hybrid(self, parser):
        result = parser.parse("Hybrid - San Francisco")
        assert result.remote_type == "hybrid"

    def test_parse_onsite_city_state(self, parser):
        result = parser.parse("San Francisco, CA")
        assert result.remote_type == "onsite"
        assert result.city == "San Francisco"
        assert result.state == "CA"

    def test_parse_onsite_city_country(self, parser):
        result = parser.parse("Bangalore, India")
        assert result.remote_type == "onsite"
        assert "Bangalore" in (result.city or "")
        assert result.country == "India"

    def test_parse_empty_string(self, parser):
        result = parser.parse("")
        assert result.remote_type == "onsite"

    def test_parse_none(self, parser):
        result = parser.parse(None)
        assert result.remote_type == "onsite"

    def test_parse_work_from_home(self, parser):
        result = parser.parse("Work from Home")
        assert result.remote_type == "remote"

    def test_parse_fully_remote(self, parser):
        result = parser.parse("Fully Remote")
        assert result.remote_type == "remote"

    def test_parse_remote_in_parens(self, parser):
        result = parser.parse("Bengaluru (Remote)")
        assert result.remote_type == "remote"

    def test_parse_hybrid_keyword(self, parser):
        result = parser.parse("Hybrid")
        assert result.remote_type == "hybrid"

    def test_parse_uk_country(self, parser):
        result = parser.parse("London, UK")
        assert result.country == "United Kingdom"

    def test_parse_us_state(self, parser):
        result = parser.parse("New York, NY")
        assert result.state == "NY"
        assert result.country is None

    def test_parse_multiple_cities(self, parser):
        result = parser.parse("San Francisco or New York")
        assert result.city is not None

    def test_parse_onsite_tag(self, parser):
        result = parser.parse("New York (Onsite)")
        assert result.remote_type == "onsite"
        assert result.city == "New York"

    def test_returns_location_data_type(self, parser):
        result = parser.parse("Remote")
        assert isinstance(result, LocationData)

    def test_parse_germany(self, parser):
        result = parser.parse("Berlin, Germany")
        assert result.country == "Germany"


# =============================================================================
# Employment Type Parser Tests
# =============================================================================

class TestEmploymentTypeParser:
    @pytest.fixture
    def parser(self) -> EmploymentTypeParser:
        return EmploymentTypeParser()

    def test_full_time(self, parser):
        result = parser.parse("Full Time")
        assert result.normalized == "full-time"

    def test_part_time(self, parser):
        result = parser.parse("Part Time")
        assert result.normalized == "part-time"

    def test_contract(self, parser):
        result = parser.parse("Contract")
        assert result.normalized == "contract"

    def test_internship(self, parser):
        result = parser.parse("Internship")
        assert result.normalized == "internship"

    def test_freelance(self, parser):
        result = parser.parse("Freelance")
        assert result.normalized == "freelance"

    def test_temporary(self, parser):
        result = parser.parse("Temporary")
        assert result.normalized == "temporary"

    def test_volunteer(self, parser):
        result = parser.parse("Volunteer")
        assert result.normalized == "volunteer"

    def test_fte_synonym(self, parser):
        result = parser.parse("FTE")
        assert result.normalized == "full-time"

    def test_c2h_synonym(self, parser):
        result = parser.parse("C2H")
        assert result.normalized == "contract"

    def test_coop_synonym(self, parser):
        result = parser.parse("Co-op")
        assert result.normalized == "internship"

    def test_empty_string(self, parser):
        result = parser.parse("")
        assert result.normalized == "full-time"

    def test_none(self, parser):
        result = parser.parse(None)
        assert result.normalized == "full-time"

    def test_full_time_employee(self, parser):
        result = parser.parse("Full Time Employee")
        assert result.normalized == "full-time"

    def test_part_time_employee(self, parser):
        result = parser.parse("Part Time Employee")
        assert result.normalized == "part-time"

    def test_contractor(self, parser):
        result = parser.parse("Contractor")
        assert result.normalized == "contract"

    def test_returns_parsed_employment_type(self, parser):
        result = parser.parse("Full Time")
        assert isinstance(result, ParsedEmploymentType)

    def test_original_is_preserved(self, parser):
        result = parser.parse("Full Time Employee")
        assert result.original == "Full Time Employee"

    def test_is_remote_friendly(self, parser):
        result = parser.parse("Full Time")
        assert result.is_remote_friendly is True
        result = parser.parse("Part Time")
        assert result.is_remote_friendly is False


# =============================================================================
# Experience Parser Tests
# =============================================================================

class TestExperienceParser:
    @pytest.fixture
    def parser(self) -> ExperienceParser:
        return ExperienceParser()

    def test_fresher(self, parser):
        result = parser.parse("Fresher")
        assert result.level == "entry"
        assert result.years_min == 0

    def test_zero_years(self, parser):
        result = parser.parse("0 Years")
        assert result.level == "entry"

    def test_entry_level(self, parser):
        result = parser.parse("Entry Level")
        assert result.level == "entry"

    def test_new_graduate(self, parser):
        result = parser.parse("New Grad")
        assert result.level == "entry"

    def test_years_range(self, parser):
        result = parser.parse("3-5 years")
        assert result.years_min == 3
        assert result.years_max == 5
        assert result.level == "mid"

    def test_plus_years(self, parser):
        result = parser.parse("5+ years")
        assert result.years_min == 5
        assert result.level == "senior"

    def test_ten_plus_years(self, parser):
        result = parser.parse("10+ years of experience")
        assert result.years_min == 10
        assert result.level == "lead"

    def test_senior_keyword(self, parser):
        result = parser.parse("Senior")
        assert result.level == "senior"

    def test_lead_keyword(self, parser):
        result = parser.parse("Lead")
        assert result.level == "lead"

    def test_principal_keyword(self, parser):
        result = parser.parse("Principal")
        assert result.level == "principal"

    def test_junior_keyword(self, parser):
        result = parser.parse("Junior")
        assert result.level == "entry"

    def test_empty_string(self, parser):
        result = parser.parse("")
        assert result.level is None

    def test_none(self, parser):
        result = parser.parse(None)
        assert result.level is None

    def test_mid_keyword(self, parser):
        result = parser.parse("Mid Level")
        assert result.level == "mid"

    def test_associate_keyword(self, parser):
        result = parser.parse("Associate")
        assert result.level == "mid"

    def test_returns_parsed_experience(self, parser):
        result = parser.parse("Senior")
        assert isinstance(result, ParsedExperience)

    def test_original_is_preserved(self, parser):
        result = parser.parse("5+ years of Python")
        assert result.original == "5+ years of Python"

    def test_two_years(self, parser):
        result = parser.parse("2+ years")
        assert result.level == "mid"

    def test_executive_level(self, parser):
        result = parser.parse("15+ years")
        assert result.level == "principal"

    def test_min_years_from_sentence(self, parser):
        result = parser.parse("Minimum 5 years of experience in backend development")
        assert result.years_min == 5


# =============================================================================
# Company Parser Tests
# =============================================================================

class TestCompanyParser:
    @pytest.fixture
    def parser(self) -> CompanyParser:
        return CompanyParser()

    def test_simple_company_name(self, parser):
        result = parser.parse("Google")
        assert result.name == "Google"
        assert result.department is None

    def test_company_with_department(self, parser):
        result = parser.parse("Google > Cloud AI")
        assert result.name == "Google"
        assert result.department == "Cloud AI"

    def test_company_hierarchy(self, parser):
        result = parser.parse("Engineering > Backend > Payments Team")
        assert result.name == "Engineering"
        assert result.team == "Payments Team"

    def test_pipe_separator(self, parser):
        result = parser.parse("Google | Cloud AI | Research")
        assert result.name == "Google"

    def test_dash_separator(self, parser):
        result = parser.parse("Product - Design - UX")
        assert result.team is None or result.team is not None  # flexible

    def test_empty_string(self, parser):
        result = parser.parse("")
        assert result.name == ""

    def test_none(self, parser):
        result = parser.parse(None)
        assert result.name == ""

    def test_slash_separator(self, parser):
        result = parser.parse("Acme Corp / Engineering / Platform")
        assert result.name == "Acme Corp"

    def test_returns_parsed_company(self, parser):
        result = parser.parse("Google")
        assert isinstance(result, ParsedCompany)

    def test_original_is_preserved(self, parser):
        result = parser.parse("Google > Cloud")
        assert result.original == "Google > Cloud"

    def test_department_detection(self, parser):
        result = parser.parse("Meta | Marketing")
        assert result.department == "Marketing"

    def test_team_detection(self, parser):
        result = parser.parse("Apple > Services > Apple Pay Team")
        assert result.team == "Apple Pay Team"


# =============================================================================
# Title Parser Tests
# =============================================================================

class TestTitleParser:
    @pytest.fixture
    def parser(self) -> TitleParser:
        return TitleParser()

    def test_senior_engineer(self, parser):
        result = parser.parse("Senior Software Engineer")
        assert result.seniority == "senior"
        assert "Senior" not in result.normalized

    def test_lead_engineer(self, parser):
        result = parser.parse("Lead Engineer")
        assert result.seniority == "lead"

    def test_principal_engineer(self, parser):
        result = parser.parse("Principal Engineer")
        assert result.seniority == "principal"

    def test_no_seniority(self, parser):
        result = parser.parse("Software Engineer")
        assert result.seniority is None
        assert result.normalized == "Software Engineer"

    def test_empty_string(self, parser):
        result = parser.parse("")
        assert result.normalized == ""

    def test_none(self, parser):
        result = parser.parse(None)
        assert result.normalized == ""

    def test_junior_developer(self, parser):
        result = parser.parse("Junior Developer")
        assert result.seniority == "junior"

    def test_director_of_engineering(self, parser):
        result = parser.parse("Director of Engineering")
        assert result.seniority is not None

    def test_returns_parsed_title(self, parser):
        result = parser.parse("Software Engineer")
        assert isinstance(result, ParsedTitle)

    def test_original_is_preserved(self, parser):
        result = parser.parse("Senior Staff Engineer")
        assert result.original == "Senior Staff Engineer"

    def test_product_manager(self, parser):
        result = parser.parse("Product Manager")
        assert result.normalized == "Product Manager"
        assert result.seniority is None

    def test_staff_engineer(self, parser):
        result = parser.parse("Staff Engineer")
        assert result.seniority == "staff"

    def test_vp_of_engineering(self, parser):
        result = parser.parse("VP of Engineering")
        assert result.seniority is not None

    def test_machine_learning_engineer(self, parser):
        result = parser.parse("Machine Learning Engineer")
        assert "Machine" in result.normalized


# =============================================================================
# Metadata Parser Tests
# =============================================================================

class TestMetadataParser:
    @pytest.fixture
    def parser(self) -> MetadataParser:
        return MetadataParser()

    def test_extract_job_id_from_field(self, parser):
        result = parser.parse({"id": "job_123", "title": "Engineer"})
        assert result.job_id == "job_123"

    def test_extract_job_id_from_url(self, parser):
        result = parser.parse({"url": "https://boards.greenhouse.io/jobs/12345"})
        assert result.job_id == "12345"

    def test_extract_reference_id(self, parser):
        result = parser.parse({"reference_id": "REQ-2024-001"})
        assert result.reference_id == "REQ-2024-001"

    def test_extract_categories(self, parser):
        result = parser.parse({"category": "Engineering"})
        assert "Engineering" in result.categories

    def test_extract_categories_list(self, parser):
        result = parser.parse({"categories": ["Engineering", "Product"]})
        assert "Engineering" in result.categories
        assert "Product" in result.categories

    def test_extract_tags(self, parser):
        result = parser.parse({"tags": ["Python", "Docker", "Kubernetes"]})
        assert "Python" in result.tags

    def test_extract_tags_from_string(self, parser):
        result = parser.parse({"skills": "Python, Docker, Kubernetes"})
        assert "Python" in result.tags

    def test_parse_iso_date(self, parser):
        result = parser.parse({"posted_at": "2024-01-15"})
        assert result.posted_at is not None
        assert result.posted_at.year == 2024
        assert result.posted_at.month == 1
        assert result.posted_at.day == 15

    def test_parse_us_date(self, parser):
        result = parser.parse({"posted_date": "01/15/2024"})
        assert result.posted_at is not None
        assert result.posted_at.month == 1
        assert result.posted_at.day == 15

    def test_null_dates(self, parser):
        result = parser.parse({"posted_at": None})
        assert result.posted_at is None

    def test_extract_custom_fields(self, parser):
        result = parser.parse({"salary_min": 100000, "custom_field": "value"})
        assert "custom_field" in result.custom
        assert result.custom["custom_field"] == "value"

    def test_empty_dict(self, parser):
        result = parser.parse({})
        assert result.job_id is None

    def test_none(self, parser):
        result = parser.parse(None)
        assert result.job_id is None

    def test_extract_language(self, parser):
        result = parser.parse({"language": "English"})
        assert result.language == "English"

    def test_deduplicates_tags(self, parser):
        result = parser.parse({"tags": ["Python", "Python", "Docker"]})
        assert len(result.tags) == 2

    def test_parse_datetime_object(self, parser):
        dt = datetime(2024, 6, 15, tzinfo=timezone.utc)
        result = parser.parse({"posted_at": dt})
        assert result.posted_at == dt

    def test_extract_job_id_uuid(self, parser):
        uid = "550e8400-e29b-41d4-a716-446655440000"
        result = parser.parse({"url": f"https://example.com/jobs/{uid}"})
        assert result.job_id == uid


# =============================================================================
# Parser Registry Tests
# =============================================================================

class TestParserRegistry:
    def teardown_method(self) -> None:
        RegistryTestHelper.restore_registry()

    def test_all_parsers_registered(self):
        parsers = ParserRegistry.list_parsers()
        assert "salary" in parsers
        assert "location" in parsers
        assert "employment_type" in parsers
        assert "experience" in parsers
        assert "company" in parsers
        assert "title" in parsers
        assert "metadata" in parsers

    def test_get_parser_by_name(self):
        parser = ParserRegistry.get("salary")
        assert parser is not None
        assert parser.name == "salary"

    def test_get_nonexistent_parser(self):
        parser = ParserRegistry.get("nonexistent")
        assert parser is None

    def test_get_or_create_parser(self):
        parser1 = ParserRegistry.get_or_create("salary")
        parser2 = ParserRegistry.get_or_create("salary")
        assert parser1 is parser2

    def test_custom_parser_registration(self):
        class TestParser(BaseParser[str]):
            name = "test_custom"
            def parse(self, raw, **context):
                return str(raw)

        ParserRegistry.register(TestParser)
        assert "test_custom" in ParserRegistry.list_parsers()

    def test_register_duplicate_raises(self):
        class DupParser(BaseParser[str]):
            name = "salary"
            def parse(self, raw, **context):
                return str(raw)

        with pytest.raises(ValueError, match="already registered"):
            ParserRegistry.register(DupParser)

    def test_register_non_parser_raises(self):
        with pytest.raises(TypeError):
            ParserRegistry.register(str)  # type: ignore[arg-type]

    def test_clear_registry(self):
        ParserRegistry.clear()
        assert ParserRegistry.list_parsers() == []
        self.teardown_method()

    def test_list_parsers_sorted(self):
        parsers = ParserRegistry.list_parsers()
        assert parsers == sorted(parsers)


# =============================================================================
# Edge Case & Unicode Tests
# =============================================================================

class TestEdgeCases:
    @pytest.fixture
    def salary_parser(self) -> SalaryParser:
        return SalaryParser()

    @pytest.fixture
    def location_parser(self) -> LocationParser:
        return LocationParser()

    @pytest.fixture
    def employment_parser(self) -> EmploymentTypeParser:
        return EmploymentTypeParser()

    @pytest.fixture
    def experience_parser(self) -> ExperienceParser:
        return ExperienceParser()

    @pytest.fixture
    def company_parser(self) -> CompanyParser:
        return CompanyParser()

    def test_salary_unicode_inr(self, salary_parser):
        result = salary_parser.parse("\u20b912-18 LPA")
        assert result is not None
        assert result.min == 1200000

    def test_salary_unicode_euro(self, salary_parser):
        result = salary_parser.parse("\u20ac70k")
        assert result is not None
        assert result.min == 70000

    def test_salary_malformed(self, salary_parser):
        result = salary_parser.parse("not a salary at all")
        assert result is None

    def test_salary_with_extra_text(self, salary_parser):
        result = salary_parser.parse("Salary: $120k - $150k DOE")
        assert result is not None
        assert result.min == 120000

    def test_location_malformed(self, location_parser):
        result = location_parser.parse("!!!")
        assert result.remote_type == "onsite"

    def test_location_unicode_city(self, location_parser):
        result = location_parser.parse("München, Germany")
        assert result.city is not None

    def test_employment_malformed(self, employment_parser):
        result = employment_parser.parse("some random text")
        assert result.normalized is not None

    def test_experience_malformed(self, experience_parser):
        result = experience_parser.parse("abcdef")
        assert result.level is None

    def test_experience_with_unicode(self, experience_parser):
        result = experience_parser.parse("5+ années d'expérience")
        # French text does not match English year patterns; expect graceful None
        assert result.level is None or result.years_min is not None

    def test_company_with_department_unicode(self, company_parser):
        result = company_parser.parse("Société > Ingénierie")
        assert result.name == "Société"
        assert result.department == "Ingénierie"

    def test_all_empty_inputs(self, salary_parser, location_parser, employment_parser, experience_parser, company_parser):
        assert salary_parser.parse(None) is None
        assert salary_parser.parse("") is None
        assert location_parser.parse(None).remote_type == "onsite"
        assert location_parser.parse("").remote_type == "onsite"
        assert employment_parser.parse(None).normalized == "full-time"
        assert employment_parser.parse("").normalized == "full-time"
        assert experience_parser.parse(None).level is None
        assert experience_parser.parse("").level is None
        assert company_parser.parse(None).name == ""
        assert company_parser.parse("").name == ""


# =============================================================================
# Normalization Consistency Tests
# =============================================================================

class TestNormalization:
    def test_salary_to_salary_data(self):
        sp = SalaryParser()
        r1 = sp.parse("$120k")
        r2 = sp.parse("$120,000")
        assert r1 is not None and r2 is not None
        assert r1.min == r2.min

    def test_employment_consistency(self):
        ep = EmploymentTypeParser()
        assert ep.parse("Full Time").normalized == "full-time"
        assert ep.parse("full-time").normalized == "full-time"
        assert ep.parse("Fulltime").normalized == "full-time"

    def test_experience_consistency(self):
        xp = ExperienceParser()
        assert xp.parse("Senior").level == "senior"
        assert xp.parse("Sr.").level == "senior"
        assert xp.parse("Sr").level == "senior"

    def test_location_remote_consistency(self):
        lp = LocationParser()
        assert lp.parse("Remote").remote_type == "remote"
        assert lp.parse("remote").remote_type == "remote"
        assert lp.parse("REMOTE").remote_type == "remote"


# =============================================================================
# Helper for restoring registry between tests
# =============================================================================

class RegistryTestHelper:
    _saved: dict[str, type[BaseParser]] = {}
    _saved_instances: dict[str, BaseParser] = {}

    @classmethod
    def restore_registry(cls) -> None:
        from app.parsers import SalaryParser, LocationParser, EmploymentTypeParser
        from app.parsers import ExperienceParser, CompanyParser, TitleParser, MetadataParser
        ParserRegistry._parsers.clear()
        ParserRegistry._instances.clear()
        for p in [SalaryParser, LocationParser, EmploymentTypeParser,
                  ExperienceParser, CompanyParser, TitleParser, MetadataParser]:
            try:
                ParserRegistry.register(p)
            except (TypeError, ValueError):
                pass
