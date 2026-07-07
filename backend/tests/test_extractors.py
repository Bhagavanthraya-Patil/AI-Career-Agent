"""Tests for the Job Details Extractor & Model Mapping layer."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from app.collectors.exceptions import ValidationError
from app.collectors.models import (
    CompanyData,
    JobData,
    JobMetadata,
    LocationData,
    SalaryData,
)
from app.extractors.base import BaseExtractor
from app.extractors.config import ExtractorConfigProvider
from app.extractors.description_extractor import DescriptionExtractor
from app.extractors.extractor_registry import ExtractorRegistry
from app.extractors.field_mapper import FieldMapper
from app.extractors.html_cleaner import HtmlCleaner
from app.extractors.job_extractor import JobExtractor
from app.extractors.location_extractor import LocationExtractor
from app.extractors.metadata_extractor import MetadataExtractor
from app.extractors.salary_extractor import SalaryExtractor


# ---------------------------------------------------------------------------
# Fixtures — realistic raw payloads for each supported source
# ---------------------------------------------------------------------------


@pytest.fixture
def greenhouse_job() -> dict[str, Any]:
    return {
        "id": 101,
        "title": "Software Engineer",
        "location": {"name": "San Francisco, CA"},
        "offices": [{"id": 1, "name": "ExampleCorp", "location": "San Francisco, CA"}],
        "departments": [{"id": 1, "name": "Engineering"}],
        "metadata": [
            {"id": 1, "name": "Employment Type", "value": "Full-time", "value_type": "single_select"},
            {"id": 2, "name": "Experience Level", "value": "Mid-Senior", "value_type": "single_select"},
            {"id": 3, "name": "Salary", "value": "$100,000 - $150,000", "value_type": "single_select"},
        ],
        "content": "<div>Job description for Software Engineer</div>",
        "absolute_url": "https://boards.greenhouse.io/exampleco/jobs/101",
        "created_at": "2026-01-15T12:00:00.000Z",
        "board_token": "exampleco",
    }


@pytest.fixture
def lever_job() -> dict[str, Any]:
    return {
        "id": "abc123",
        "text": "Senior Frontend Engineer",
        "categories": {
            "location": "Remote, United States",
            "team": "Frontend Team",
            "commitment": "Full-Time",
        },
        "description": "<p>Frontend role description</p>",
        "descriptionPlain": "Frontend role description",
        "additional": "$150,000 - $200,000",
        "hostedUrl": "https://jobs.lever.co/exampleco/abc123",
        "createdAt": 1736938800000,
        "lists": [],
    }


@pytest.fixture
def ashby_job() -> dict[str, Any]:
    return {
        "id": "job_456",
        "title": "Backend Engineer",
        "companyName": "AshbyCorp",
        "locations": ["New York, NY, United States"],
        "type": "Full-time",
        "department": "Engineering",
        "description": "<div><p>Backend role description</p></div>",
        "compensationSummary": "$120,000 - $180,000",
        "postingUrl": "https://jobs.ashbyhq.com/ashbycorp/job_456",
        "applyUrl": "https://jobs.ashbyhq.com/ashbycorp/job_456/apply",
        "publishedAt": "2026-01-15T12:00:00Z",
    }


@pytest.fixture
def workday_job() -> dict[str, Any]:
    return {
        "title": "DevOps Engineer",
        "company": "WorkdayInc",
        "location": "San Francisco, CA, United States",
        "bulletFields": ["Senior", "Full-time", "Remote"],
        "jobPostingInfo": {
            "jobDescription": "<div><p>DevOps role description</p></div>",
        },
        "externalPath": "/en-US/ExampleCo/job/San-Francisco/DevOps-Engineer_R12345",
        "jobPostingId": "R12345",
        "postedOn": "2026-01-20T08:00:00.000Z",
    }


@pytest.fixture
def remoteok_job() -> dict[str, Any]:
    return {
        "id": "789",
        "title": "Full Stack Developer",
        "company": "RemoteOK Inc",
        "company_logo": "https://remoteok.com/logo.png",
        "location": "Remote",
        "salary_min": 80000,
        "salary_max": 120000,
        "tags": ["full-time", "react", "python", "aws"],
        "description": "<p>Full stack developer role</p>",
        "url": "https://remoteok.com/remote-jobs/789",
        "apply_url": "https://remoteok.com/remote-jobs/789/apply",
        "date": "2026-02-01",
    }


# ---------------------------------------------------------------------------
# HtmlCleaner Tests
# ---------------------------------------------------------------------------


class TestHtmlCleaner:
    def test_strip_html_basic(self):
        assert HtmlCleaner.strip_html("<p>Hello</p>") == "Hello"

    def test_strip_html_with_scripts(self):
        html = "<div>Text</div><script>alert('x')</script><style>.cls{}</style>"
        result = HtmlCleaner.strip_html(html)
        assert "alert" not in result
        assert ".cls" not in result
        assert "Text" in result

    def test_strip_html_empty(self):
        assert HtmlCleaner.strip_html("") == ""
        assert HtmlCleaner.strip_html(None) == ""

    def test_strip_markdown_basic(self):
        md = "**bold** and *italic* and `code`"
        result = HtmlCleaner.strip_markdown(md)
        assert "bold" in result
        assert "italic" in result
        assert "**" not in result
        assert "*" not in result

    def test_strip_markdown_links(self):
        md = "Click [here](https://example.com) for info"
        result = HtmlCleaner.strip_markdown(md)
        assert result == "Click here for info"

    def test_strip_markdown_headers(self):
        md = "# Title\n\nParagraph"
        result = HtmlCleaner.strip_markdown(md)
        assert "#" not in result
        assert "Title" in result

    def test_to_plain_text_html(self):
        result = HtmlCleaner.to_plain_text("<div><p>Hello World</p></div>")
        assert "Hello World" in result
        assert "<" not in result

    def test_to_plain_text_markdown(self):
        result = HtmlCleaner.to_plain_text("**Hello** *World*")
        assert "Hello" in result
        assert "World" in result

    def test_to_plain_text_plain(self):
        result = HtmlCleaner.to_plain_text("Just plain text")
        assert result == "Just plain text"

    def test_normalize_whitespace(self):
        assert HtmlCleaner.normalize_whitespace("  hello   world  ") == "hello world"

    def test_is_html(self):
        assert HtmlCleaner.is_html("<div>test</div>") is True
        assert HtmlCleaner.is_html("plain text") is False

    def test_is_markdown(self):
        assert HtmlCleaner.is_markdown("**bold**") is True
        assert HtmlCleaner.is_markdown("plain text") is False


# ---------------------------------------------------------------------------
# FieldMapper Tests
# ---------------------------------------------------------------------------


class TestFieldMapper:
    def test_greenhouse_mapping(self, greenhouse_job):
        result = FieldMapper.map(greenhouse_job, "greenhouse")
        assert result["title"] == "Software Engineer"
        assert result["company_name"] == "ExampleCorp"
        assert result["location_raw"] == "San Francisco, CA"
        assert result["salary_raw"] == "$100,000 - $150,000"
        assert result["employment_type_raw"] == "full-time"
        assert result["experience_level_raw"] == "mid-senior"
        assert result["description_html"] == "<div>Job description for Software Engineer</div>"
        assert result["job_url"] == "https://boards.greenhouse.io/exampleco/jobs/101"
        assert result["source_job_id"] == "101"
        assert result["source"] == "greenhouse"
        assert result["is_remote"] is None

    def test_greenhouse_remote_job(self):
        job = {
            "id": 102,
            "title": "Remote Engineer",
            "location": {"name": "Remote, United States"},
            "offices": [{"id": 1, "name": "Co", "location": "Remote"}],
            "metadata": [
                {"id": 4, "name": "Remote", "value": "Remote", "value_type": "single_select"},
            ],
            "content": "",
            "absolute_url": "https://boards.greenhouse.io/co/jobs/102",
            "created_at": "2026-01-15T12:00:00.000Z",
        }
        result = FieldMapper.map(job, "greenhouse")
        assert result["is_remote"] == "remote"

    def test_lever_mapping(self, lever_job):
        result = FieldMapper.map(lever_job, "lever")
        assert result["title"] == "Senior Frontend Engineer"
        assert result["company_name"] == "Frontend Team"
        assert result["location_raw"] == "Remote, United States"
        assert result["salary_raw"] == "$150,000 - $200,000"
        assert result["employment_type_raw"] == "Full-Time"
        assert result["description_html"] == "<p>Frontend role description</p>"
        assert result["description_raw"] == "Frontend role description"
        assert result["job_url"] == "https://jobs.lever.co/exampleco/abc123"
        assert result["source_job_id"] == "abc123"
        assert result["source"] == "lever"

    def test_ashby_mapping(self, ashby_job):
        result = FieldMapper.map(ashby_job, "ashby")
        assert result["title"] == "Backend Engineer"
        assert result["company_name"] == "AshbyCorp"
        assert result["location_raw"] == "New York, NY, United States"
        assert result["salary_raw"] == "$120,000 - $180,000"
        assert result["employment_type_raw"] == "Full-time"
        assert result["description_html"] == "<div><p>Backend role description</p></div>"
        assert result["job_url"] == "https://jobs.ashbyhq.com/ashbycorp/job_456"
        assert result["source_job_id"] == "job_456"
        assert result["source"] == "ashby"

    def test_workday_mapping(self, workday_job):
        result = FieldMapper.map(workday_job, "workday")
        assert result["title"] == "DevOps Engineer"
        assert result["company_name"] == "WorkdayInc"
        assert result["location_raw"] == "San Francisco, CA, United States"
        assert result["employment_type_raw"] == "full-time"
        assert result["description_html"] == "<div><p>DevOps role description</p></div>"
        assert result["source_job_id"] == "R12345"
        assert result["source"] == "workday"
        assert result["is_remote"] == "remote"

    def test_remoteok_mapping(self, remoteok_job):
        result = FieldMapper.map(remoteok_job, "remoteok")
        assert result["title"] == "Full Stack Developer"
        assert result["company_name"] == "RemoteOK Inc"
        assert result["company_logo"] == "https://remoteok.com/logo.png"
        assert result["location_raw"] == "Remote"
        assert result["salary_min_raw"] == 80000
        assert result["salary_max_raw"] == 120000
        assert result["employment_type_raw"] == "full-time"
        assert result["tags"] == ["full-time", "react", "python", "aws"]
        assert result["skills_raw"] == ["full-time", "react", "python", "aws"]
        assert result["job_url"] == "https://remoteok.com/remote-jobs/789"
        assert result["source_job_id"] == "789"
        assert result["source"] == "remoteok"
        assert result["is_remote"] == "remote"

    def test_unknown_source_mapping(self):
        raw = {
            "title": "Custom Role",
            "company": "CustomCo",
            "location": "London, UK",
            "description": "<p>Custom description</p>",
            "url": "https://custom.com/jobs/1",
            "id": 1,
        }
        result = FieldMapper.map(raw, "custom_source")
        assert result["title"] == "Custom Role"
        assert result["company_name"] == "CustomCo"
        assert result["location_raw"] == "London, UK"
        assert result["source"] == "custom_source"
        assert result["source_job_id"] == "1"

    def test_register_custom_source(self):
        FieldMapper.register_source("test_source", {
            "title": lambda d: d.get("name", ""),
            "company_name": lambda d: d.get("org", ""),
        })
        result = FieldMapper.map({"name": "Tester", "org": "TestOrg"}, "test_source")
        assert result["title"] == "Tester"
        assert result["company_name"] == "TestOrg"

    def test_empty_input(self):
        result = FieldMapper.map({}, "greenhouse")
        assert result["title"] == ""
        assert result["source"] == "greenhouse"


# ---------------------------------------------------------------------------
# BaseExtractor / ExtractorRegistry Tests
# ---------------------------------------------------------------------------


class TestExtractorRegistry:
    def setup_method(self):
        ExtractorRegistry.clear()

    def test_register_and_get(self):
        ExtractorRegistry.clear()
        ExtractorRegistry.register(SalaryExtractor)
        instance = ExtractorRegistry.get("salary")
        assert instance is not None
        assert isinstance(instance, SalaryExtractor)

    def test_get_nonexistent(self):
        assert ExtractorRegistry.get("nonexistent") is None

    def test_list_extractors(self):
        ExtractorRegistry.clear()
        ExtractorRegistry.register(SalaryExtractor)
        ExtractorRegistry.register(LocationExtractor)
        names = ExtractorRegistry.list_extractors()
        assert "salary" in names
        assert "location" in names

    def test_register_duplicate_raises(self):
        ExtractorRegistry.clear()
        ExtractorRegistry.register(SalaryExtractor)
        with pytest.raises(ValueError, match="already registered"):
            ExtractorRegistry.register(SalaryExtractor)

    def test_register_non_extractor_raises(self):
        with pytest.raises(TypeError):
            ExtractorRegistry.register(str)  # type: ignore

    def test_get_or_create_caches(self):
        ExtractorRegistry.clear()
        ExtractorRegistry.register(SalaryExtractor)
        a = ExtractorRegistry.get_or_create("salary")
        b = ExtractorRegistry.get_or_create("salary")
        assert a is b

    def test_clear(self):
        ExtractorRegistry.clear()
        ExtractorRegistry.register(SalaryExtractor)
        ExtractorRegistry.clear()
        assert ExtractorRegistry.list_extractors() == []


# ---------------------------------------------------------------------------
# DescriptionExtractor Tests
# ---------------------------------------------------------------------------


class TestDescriptionExtractor:
    def test_extract_html(self):
        extractor = DescriptionExtractor()
        desc_raw, desc_html = extractor.extract({"description_html": "<div><p>Hello</p></div>"})
        assert "Hello" in desc_raw
        assert "<div><p>Hello</p>" in desc_html

    def test_extract_plain_text(self):
        extractor = DescriptionExtractor()
        desc_raw, desc_html = extractor.extract({"description_raw": "Hello world"})
        assert desc_raw == "Hello world"
        assert desc_html is None

    def test_extract_raw_string_html(self):
        extractor = DescriptionExtractor()
        desc_raw, desc_html = extractor.extract("<div><p>Test</p></div>")
        assert desc_raw == "Test"
        assert desc_html == "<div><p>Test</p></div>"

    def test_extract_raw_string_plain(self):
        extractor = DescriptionExtractor()
        desc_raw, desc_html = extractor.extract("Just text")
        assert desc_raw == "Just text"
        assert desc_html is None

    def test_extract_none(self):
        extractor = DescriptionExtractor()
        desc_raw, desc_html = extractor.extract(None)
        assert desc_raw is None
        assert desc_html is None

    def test_extract_empty(self):
        extractor = DescriptionExtractor()
        desc_raw, desc_html = extractor.extract({})
        assert desc_raw is None
        assert desc_html is None

    def test_extract_handles_html_and_plain(self):
        extractor = DescriptionExtractor()
        desc_raw, desc_html = extractor.extract({
            "description_html": "<p>HTML</p>",
            "description_raw": "Plain",
        })
        assert desc_raw == "Plain"
        assert "<p>HTML</p>" in desc_html


# ---------------------------------------------------------------------------
# SalaryExtractor Tests
# ---------------------------------------------------------------------------


class TestSalaryExtractor:
    def test_extract_from_string(self):
        extractor = SalaryExtractor()
        result = extractor.extract("$100,000 - $150,000")
        assert result is not None
        assert result.min == 100000
        assert result.max == 150000
        assert result.currency == "USD"

    def test_extract_from_dict_salary_raw(self):
        extractor = SalaryExtractor()
        result = extractor.extract({"salary_raw": "$80,000 - $120,000"})
        assert result is not None
        assert result.min == 80000
        assert result.max == 120000

    def test_extract_from_dict_numeric(self):
        extractor = SalaryExtractor()
        result = extractor.extract({"salary_min_raw": 90000, "salary_max_raw": 130000})
        assert result is not None
        assert result.min == 90000
        assert result.max == 130000

    def test_extract_from_dict_numeric_min_only(self):
        extractor = SalaryExtractor()
        result = extractor.extract({"salary_min_raw": 75000})
        assert result is not None
        assert result.min == 75000
        assert result.max is None

    def test_extract_none(self):
        extractor = SalaryExtractor()
        assert extractor.extract(None) is None
        assert extractor.extract({}) is None
        assert extractor.extract("") is None

    def test_extract_with_currency_and_interval(self):
        extractor = SalaryExtractor()
        result = extractor.extract({
            "salary_min_raw": 50000,
            "salary_max_raw": 70000,
            "currency": "EUR",
            "interval": "monthly",
        })
        assert result is not None
        assert result.min == 50000
        assert result.max == 70000
        assert result.currency == "EUR"
        assert result.interval == "monthly"

    def test_extract_greenhouse_salary(self, greenhouse_job):
        extractor = SalaryExtractor()
        canonical = FieldMapper.map(greenhouse_job, "greenhouse")
        result = extractor.extract(canonical)
        assert result is not None
        assert result.min == 100000
        assert result.max == 150000


# ---------------------------------------------------------------------------
# LocationExtractor Tests
# ---------------------------------------------------------------------------


class TestLocationExtractor:
    def test_extract_from_dict(self):
        extractor = LocationExtractor()
        result = extractor.extract({"location_raw": "San Francisco, CA"})
        assert result.city == "San Francisco"
        assert result.state == "CA"
        assert result.remote_type == "onsite"

    def test_extract_remote(self):
        extractor = LocationExtractor()
        result = extractor.extract({"location_raw": "Remote", "is_remote": "remote"})
        assert result.remote_type == "remote"

    def test_extract_remote_override(self):
        extractor = LocationExtractor()
        result = extractor.extract({"location_raw": "", "is_remote": "remote"})
        assert result.remote_type == "remote"

    def test_extract_hybrid_override(self):
        extractor = LocationExtractor()
        result = extractor.extract({"location_raw": "New York, NY", "is_remote": "hybrid"})
        assert result.remote_type == "hybrid"

    def test_extract_from_string(self):
        extractor = LocationExtractor()
        result = extractor.extract("London, UK")
        assert result.city == "London"
        assert result.country == "United Kingdom"

    def test_extract_empty(self):
        extractor = LocationExtractor()
        result = extractor.extract({})
        assert result.remote_type == "onsite"
        assert result.city is None

    def test_extract_greenhouse_location(self, greenhouse_job):
        extractor = LocationExtractor()
        canonical = FieldMapper.map(greenhouse_job, "greenhouse")
        result = extractor.extract(canonical)
        assert result.city == "San Francisco"
        assert result.state == "CA"
        assert result.remote_type == "onsite"


# ---------------------------------------------------------------------------
# MetadataExtractor Tests
# ---------------------------------------------------------------------------


class TestMetadataExtractor:
    def test_extract_basic(self):
        extractor = MetadataExtractor()
        result = extractor.extract({
            "source": "greenhouse",
            "source_job_id": "101",
            "job_url": "https://example.com/jobs/101",
            "company_name": "ExampleCorp",
            "employment_type_raw": "full-time",
            "experience_level_raw": "senior",
        })
        assert result["source"] == "greenhouse"
        assert result["source_job_id"] == "101"
        assert result["job_url"] == "https://example.com/jobs/101"
        assert result["company_name"] == "ExampleCorp"
        assert result["employment_type"] == "full-time"
        assert result["experience_level"] == "senior"

    def test_extract_posted_at_iso(self):
        extractor = MetadataExtractor()
        result = extractor.extract({"posted_at_raw": "2026-01-15T12:00:00Z"})
        assert result["posted_at"] is not None
        assert result["posted_at"].year == 2026
        assert result["posted_at"].month == 1

    def test_extract_posted_at_ms_epoch(self):
        extractor = MetadataExtractor()
        result = extractor.extract({"posted_at_raw_ms": 1768474800000})
        assert result["posted_at"] is not None
        assert result["posted_at"].year == 2026

    def test_extract_posted_at_epoch_seconds(self):
        extractor = MetadataExtractor()
        result = extractor.extract({"posted_at_raw": "1736938800"})
        assert result["posted_at"] is not None

    def test_extract_posted_at_empty(self):
        extractor = MetadataExtractor()
        result = extractor.extract({})
        assert result["posted_at"] is None

    def test_extract_skills_and_tags(self):
        extractor = MetadataExtractor()
        result = extractor.extract({
            "skills_raw": ["python", "react"],
            "tags": ["full-time", "remote"],
        })
        assert result["skills"] == ["python", "react"]
        assert result["tags"] == ["full-time", "remote"]

    def test_build_job_metadata(self):
        extractor = MetadataExtractor()
        meta = extractor.build_job_metadata({
            "source": "greenhouse",
            "source_job_id": "101",
            "job_url": "https://example.com/jobs/101",
            "apply_url": "https://example.com/apply/101",
        })
        assert isinstance(meta, JobMetadata)
        assert meta.source == "greenhouse"
        assert meta.source_job_id == "101"

    def test_build_company_data(self):
        extractor = MetadataExtractor()
        company = extractor.build_company_data({
            "company_name": "TestCo",
            "company_logo": "https://example.com/logo.png",
        })
        assert isinstance(company, CompanyData)
        assert company.name == "TestCo"
        assert company.logo_url == "https://example.com/logo.png"


# ---------------------------------------------------------------------------
# JobExtractor (Integration) Tests
# ---------------------------------------------------------------------------


class TestJobExtractor:
    def test_extract_greenhouse(self, greenhouse_job):
        extractor = JobExtractor()
        job = extractor.extract(greenhouse_job, source="greenhouse")
        assert isinstance(job, JobData)
        assert job.title == "Software Engineer"
        assert job.company.name == "ExampleCorp"
        assert job.location.city == "San Francisco"
        assert job.location.state == "CA"
        assert job.metadata.source == "greenhouse"
        assert job.metadata.source_job_id == "101"
        assert job.metadata.job_url == "https://boards.greenhouse.io/exampleco/jobs/101"
        assert job.salary is not None
        assert job.salary.min == 100000
        assert job.salary.max == 150000
        assert job.employment_type == "full-time"
        assert job.experience_level == "mid-senior"
        assert "Job description for Software Engineer" in job.description_raw
        assert job.description_html is not None

    def test_extract_lever(self, lever_job):
        extractor = JobExtractor()
        job = extractor.extract(lever_job, source="lever")
        assert job.title == "Senior Frontend Engineer"
        assert job.company.name == "Frontend Team"
        assert job.location.remote_type == "remote"
        assert job.metadata.source == "lever"
        assert job.metadata.source_job_id == "abc123"
        assert job.salary is not None
        assert job.salary.min == 150000
        assert job.employment_type == "full-time"  # normalized by parser

    def test_extract_ashby(self, ashby_job):
        extractor = JobExtractor()
        job = extractor.extract(ashby_job, source="ashby")
        assert job.title == "Backend Engineer"
        assert job.company.name == "AshbyCorp"
        assert job.location.city == "New York"
        assert job.metadata.source == "ashby"
        assert job.metadata.source_job_id == "job_456"
        assert job.salary is not None
        assert job.salary.min == 120000
        assert job.salary.max == 180000
        assert job.employment_type == "full-time"
        assert len(job.skills) > 0

    def test_extract_workday(self, workday_job):
        extractor = JobExtractor()
        job = extractor.extract(workday_job, source="workday")
        assert job.title == "DevOps Engineer"
        assert job.company.name == "WorkdayInc"
        assert job.location.city == "San Francisco"
        assert job.metadata.source == "workday"
        assert job.metadata.source_job_id == "R12345"
        assert job.employment_type == "full-time"
        assert job.experience_level == "senior"
        assert job.location.remote_type == "remote"

    def test_extract_remoteok(self, remoteok_job):
        extractor = JobExtractor()
        job = extractor.extract(remoteok_job, source="remoteok")
        assert job.title == "Full Stack Developer"
        assert job.company.name == "RemoteOK Inc"
        assert job.company.logo_url == "https://remoteok.com/logo.png"
        assert job.location.remote_type == "remote"
        assert job.metadata.source == "remoteok"
        assert job.metadata.source_job_id == "789"
        assert job.salary is not None
        assert job.salary.min == 80000
        assert job.salary.max == 120000
        assert job.employment_type == "full-time"
        assert "react" in job.skills
        assert "python" in job.skills
        assert "aws" in job.skills

    def test_extract_empty_job_raises(self):
        extractor = JobExtractor()
        with pytest.raises(ValidationError, match="title is required"):
            extractor.extract({}, source="greenhouse")

    def test_extract_job_without_id_raises(self):
        extractor = JobExtractor()
        with pytest.raises(ValidationError, match="job ID is required"):
            extractor.extract({"title": "Test"}, source="greenhouse")

    def test_extract_batch(self, greenhouse_job):
        extractor = JobExtractor()
        results = extractor.extract_batch(
            [greenhouse_job, greenhouse_job],
            source="greenhouse",
        )
        assert len(results) == 2
        assert results[0].title == "Software Engineer"
        assert results[1].title == "Software Engineer"

    def test_extract_batch_skips_invalid(self):
        extractor = JobExtractor()
        results = extractor.extract_batch(
            [{"title": "Valid", "id": 1, "absolute_url": "url"}, {}],
            source="greenhouse",
        )
        assert len(results) == 1
        assert results[0].title == "Valid"


# ---------------------------------------------------------------------------
# ExtractorConfigProvider Tests
# ---------------------------------------------------------------------------


class TestExtractorConfigProvider:
    def test_get_all_returns_dict(self):
        config = ExtractorConfigProvider.get_all()
        assert isinstance(config, dict)
        assert "salary_default_currency" in config
        assert "location_remote_keywords" in config

    def test_get_salary_config(self):
        config = ExtractorConfigProvider.get_salary_config()
        assert config["default_currency"] == "USD"
        assert config["default_interval"] == "yearly"

    def test_get_location_config(self):
        config = ExtractorConfigProvider.get_location_config()
        assert "remote" in config["remote_keywords"]

    def test_get_employment_config(self):
        config = ExtractorConfigProvider.get_employment_config()
        assert "full time" in config["synonyms"]

    def test_get_experience_config(self):
        config = ExtractorConfigProvider.get_experience_config()
        assert "entry" in config["level_keywords"]
        assert "entry" in config["year_ranges"]

    def test_get_title_config(self):
        config = ExtractorConfigProvider.get_title_config()
        assert "senior" in config["seniority_prefixes"]

    def test_get_metadata_config(self):
        config = ExtractorConfigProvider.get_metadata_config()
        assert "date_formats" in config
        assert "default_categories" in config
