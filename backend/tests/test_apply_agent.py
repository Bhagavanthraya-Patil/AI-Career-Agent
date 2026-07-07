from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.apply_agent import (
    ApplyAgent,
    ApplyAgentConfig,
    ApplyAgentInput,
    ApplicationContext,
    ApplicationResult,
    ApplicationSession,
    ApplyError,
    BrowserCleanupError,
    CoverLetterGenerator,
    FieldFillError,
    FieldFiller,
    FieldMapper,
    FormDetector,
    FormDetectionError,
    FormField,
    NavigationError,
    QuestionAnswerer,
    ResumeUploader,
    StateMachine,
    ApplicationState,
    StateTransitionError,
    SubmissionError,
    SubmitHandler,
    TimeoutError,
    UnsupportedFormError,
    UploadError,
    UploadedDocument,
    UserProfile,
    ValidationError,
    VerificationError,
    check_preconditions,
    validate_file_path,
    validate_form_fields,
    validate_required_fields_filled,
    validate_user_profile,
)
from app.collectors.models import CompanyData, JobData, JobMetadata, LocationData, SalaryData


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_job() -> JobData:
    return JobData(
        title="Software Engineer",
        company=CompanyData(name="TestCorp"),
        location=LocationData(city="San Francisco", state="CA", full_address="San Francisco, CA"),
        salary=SalaryData(min=100000, max=150000, currency="USD", interval="yearly"),
        description_raw="We are looking for a skilled engineer...",
        metadata=JobMetadata(
            source="greenhouse",
            source_job_id="ext-123",
            job_url="https://boards.greenhouse.io/testcorp/jobs/123",
            posted_at=datetime(2026, 1, 15, tzinfo=timezone.utc),
        ),
        employment_type="Full-time",
        experience_level="Mid-Senior",
    )


@pytest.fixture
def sample_profile() -> UserProfile:
    return UserProfile(
        personal_details={
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "phone": "+1-555-1234",
            "city": "San Francisco",
            "state": "CA",
            "country": "United States",
        },
        work_history=[
            {"company": "PrevCorp", "title": "Junior Engineer", "years": "2020-2023"},
        ],
        skills=["Python", "TypeScript", "React"],
    )


def make_mock_page() -> MagicMock:
    page = MagicMock()
    page.locator = MagicMock(return_value=MagicMock())
    page.query_selector_all = AsyncMock(return_value=[])
    page.query_selector = AsyncMock(return_value=None)
    page.inner_text = AsyncMock(return_value="")
    page.screenshot = AsyncMock(return_value=None)
    page.wait_for_load_state = AsyncMock()
    return page


def make_mock_browser_session() -> MagicMock:
    session = MagicMock()
    session.navigate = AsyncMock()
    session.current_page = MagicMock()
    session.current_page.return_value = make_mock_page()
    session.close = AsyncMock()
    session.is_closed = MagicMock(return_value=False)
    session.screenshot = AsyncMock(return_value=None)
    return session


# ---------------------------------------------------------------------------
# StateMachine Tests
# ---------------------------------------------------------------------------


class TestStateMachine:
    def test_initial_state(self):
        sm = StateMachine()
        assert sm.state == ApplicationState.INITIALIZED

    def test_valid_transition(self):
        sm = StateMachine()
        sm.transition_to(ApplicationState.PAGE_LOADED)
        assert sm.state == ApplicationState.PAGE_LOADED

    def test_invalid_transition_raises(self):
        sm = StateMachine()
        with pytest.raises(StateTransitionError) as exc:
            sm.transition_to(ApplicationState.VERIFIED)
        assert "initialized" in str(exc.value).lower()
        assert "verified" in str(exc.value).lower()

    def test_transition_records_history(self):
        sm = StateMachine()
        sm.transition_to(ApplicationState.PAGE_LOADED, reason="navigated")
        sm.transition_to(ApplicationState.ANALYZED, reason="fields detected")
        assert len(sm.history) == 2
        assert sm.history[0] == (ApplicationState.INITIALIZED, ApplicationState.PAGE_LOADED, "navigated")
        assert sm.history[1] == (ApplicationState.PAGE_LOADED, ApplicationState.ANALYZED, "fields detected")

    def test_full_lifecycle(self):
        sm = StateMachine()
        states = [
            ApplicationState.PAGE_LOADED,
            ApplicationState.ANALYZED,
            ApplicationState.FILLED,
            ApplicationState.UPLOADED,
            ApplicationState.REVIEWED,
            ApplicationState.SUBMITTED,
            ApplicationState.VERIFIED,
        ]
        for s in states:
            sm.transition_to(s)
        assert sm.state == ApplicationState.VERIFIED

    def test_failed_transition_to_initialized(self):
        sm = StateMachine()
        sm.transition_to(ApplicationState.PAGE_LOADED)
        sm.transition_to(ApplicationState.FAILED)
        assert sm.state == ApplicationState.FAILED
        sm.transition_to(ApplicationState.INITIALIZED)
        assert sm.state == ApplicationState.INITIALIZED

    def test_can_transition_to(self):
        sm = StateMachine()
        assert sm.can_transition_to(ApplicationState.PAGE_LOADED)
        assert not sm.can_transition_to(ApplicationState.VERIFIED)

    def test_cancelled_is_terminal(self):
        sm = StateMachine()
        sm.transition_to(ApplicationState.CANCELLED)
        assert sm.can_transition_to(ApplicationState.INITIALIZED) is False

    def test_verified_is_terminal(self):
        sm = StateMachine()
        sm.transition_to(ApplicationState.PAGE_LOADED)
        sm.transition_to(ApplicationState.ANALYZED)
        sm.transition_to(ApplicationState.FILLED)
        sm.transition_to(ApplicationState.UPLOADED)
        sm.transition_to(ApplicationState.REVIEWED)
        sm.transition_to(ApplicationState.SUBMITTED)
        sm.transition_to(ApplicationState.VERIFIED)
        assert sm.can_transition_to(ApplicationState.INITIALIZED) is False

    def test_skip_from_initialized_to_cancelled(self):
        sm = StateMachine()
        sm.transition_to(ApplicationState.CANCELLED)
        assert sm.state == ApplicationState.CANCELLED


# ---------------------------------------------------------------------------
# FormField, UserProfile, UploadedDocument, ApplicationContext Tests
# ---------------------------------------------------------------------------


class TestFormField:
    def test_default_values(self):
        f = FormField()
        assert f.element_type == "text"
        assert f.selector == ""
        assert f.label == ""
        assert f.name == ""
        assert f.required is False
        assert f.field_type == "unknown"

    def test_custom_values(self):
        f = FormField(
            element_type="dropdown",
            selector="#country",
            label="Country",
            name="country",
            required=True,
            field_type="country",
            options=["US", "CA"],
            value="US",
        )
        assert f.element_type == "dropdown"
        assert f.value == "US"
        assert f.options == ["US", "CA"]


class TestUserProfile:
    def test_default_empty(self):
        p = UserProfile()
        assert p.personal_details == {}
        assert p.work_history == []
        assert p.education == []
        assert p.skills == []

    def test_with_data(self):
        p = UserProfile(
            personal_details={"first_name": "John"},
            skills=["Python"],
        )
        assert p.personal_details["first_name"] == "John"
        assert "Python" in p.skills


class TestUploadedDocument:
    def test_default(self):
        d = UploadedDocument()
        assert d.uploaded is False
        assert d.error is None

    def test_success(self):
        d = UploadedDocument(field_selector="input[type=file]", file_path="/tmp/resume.pdf", uploaded=True)
        assert d.uploaded is True
        assert d.file_path == "/tmp/resume.pdf"


class TestApplicationContext:
    def test_defaults(self, sample_job):
        ctx = ApplicationContext(job=sample_job)
        assert ctx.job.title == "Software Engineer"
        assert ctx.state == ApplicationState.INITIALIZED
        assert ctx.mode == "review"
        assert ctx.errors == []

    def test_add_error(self, sample_job):
        ctx = ApplicationContext(job=sample_job)
        ctx.add_error("Something went wrong")
        assert ctx.has_errors()
        assert "Something went wrong" in ctx.errors

    def test_form_fields(self, sample_job):
        ctx = ApplicationContext(job=sample_job)
        fields = [FormField(label="Email", name="email")]
        ctx.form_fields = fields
        assert len(ctx.form_fields) == 1


# ---------------------------------------------------------------------------
# ApplicationResult Tests
# ---------------------------------------------------------------------------


class TestApplicationResult:
    def test_default_failure(self):
        r = ApplicationResult()
        assert r.success is False
        assert r.errors == []

    def test_summary_success_with_confirmation(self):
        r = ApplicationResult(success=True, confirmation_code="CONF-123")
        assert "submitted successfully" in r.summary
        assert "CONF-123" in r.summary

    def test_summary_review_mode(self):
        r = ApplicationResult(success=True, confirmation_code=None)
        assert "review/dry-run" in r.summary

    def test_summary_failure(self):
        r = ApplicationResult(success=False, errors=["Network error"])
        assert "Network error" in r.summary

    def test_to_dict(self):
        r = ApplicationResult(success=True, final_state=ApplicationState.VERIFIED, duration_seconds=12.5)
        d = r.to_dict()
        assert d["success"] is True
        assert d["final_state"] == "verified"
        assert d["duration_seconds"] == 12.5


# ---------------------------------------------------------------------------
# ApplicationSession Tests
# ---------------------------------------------------------------------------


class TestApplicationSession:
    @pytest.mark.asyncio
    async def test_navigate(self):
        mock_browser = make_mock_browser_session()
        session = ApplicationSession(browser_session=mock_browser)
        await session.navigate("https://example.com/apply")
        mock_browser.navigate.assert_called_once_with(
            url="https://example.com/apply",
            timeout=30000,
            wait_until="networkidle",
        )

    @pytest.mark.asyncio
    async def test_navigate_failure_raises(self):
        mock_browser = make_mock_browser_session()
        mock_browser.navigate = AsyncMock(side_effect=Exception("timeout"))
        session = ApplicationSession(browser_session=mock_browser)
        with pytest.raises(NavigationError):
            await session.navigate("https://example.com/apply")

    @pytest.mark.asyncio
    async def test_close(self):
        mock_browser = make_mock_browser_session()
        session = ApplicationSession(browser_session=mock_browser)
        await session.close()
        mock_browser.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_idempotent(self):
        mock_browser = make_mock_browser_session()
        mock_browser.is_closed = MagicMock(return_value=True)
        session = ApplicationSession(browser_session=mock_browser)
        await session.close()
        mock_browser.close.assert_not_called()

    @pytest.mark.asyncio
    async def test_current_page(self):
        mock_browser = make_mock_browser_session()
        session = ApplicationSession(browser_session=mock_browser)
        page = session.current_page
        assert page is not None

    @pytest.mark.asyncio
    async def test_navigation_count(self):
        mock_browser = make_mock_browser_session()
        session = ApplicationSession(browser_session=mock_browser)
        assert session.navigation_count == 0
        await session.navigate("https://example.com/apply")
        assert session.navigation_count == 1

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        mock_browser = make_mock_browser_session()
        async with ApplicationSession(browser_session=mock_browser) as session:
            assert session is not None
        mock_browser.close.assert_called_once()


# ---------------------------------------------------------------------------
# Exceptions Tests
# ---------------------------------------------------------------------------


class TestExceptions:
    def test_apply_error_base(self):
        err = ApplyError("base error", step="test")
        assert str(err) == "base error"
        assert err.step == "test"

    def test_apply_error_with_original(self):
        original = ValueError("inner")
        err = ApplyError("wrapped", original=original)
        assert err.original is original

    def test_field_fill_error(self):
        err = FieldFillError("field error", field_name="email", field_type="email")
        assert err.field_name == "email"
        assert err.field_type == "email"

    def test_validation_error_with_errors(self):
        err = ValidationError("bad data", errors=["field1 missing", "field2 missing"])
        assert len(err.errors) == 2

    def test_state_transition_error(self):
        err = StateTransitionError("invalid", current_state="a", target_state="b")
        assert err.current_state == "a"
        assert err.target_state == "b"

    def test_hierarchy(self):
        assert issubclass(NavigationError, ApplyError)
        assert issubclass(SubmissionError, ApplyError)
        assert issubclass(UploadError, ApplyError)
        assert issubclass(VerificationError, ApplyError)
        assert issubclass(ValidationError, ApplyError)
        assert issubclass(TimeoutError, ApplyError)
        assert issubclass(UnsupportedFormError, ApplyError)
        assert issubclass(BrowserCleanupError, ApplyError)


# ---------------------------------------------------------------------------
# Validation Tests
# ---------------------------------------------------------------------------


class TestValidateUserProfile:
    def test_valid_profile(self, sample_profile):
        errors = validate_user_profile(sample_profile)
        assert errors == []

    def test_missing_required_fields(self):
        profile = UserProfile(personal_details={})
        errors = validate_user_profile(profile)
        assert len(errors) == 4  # 3 required fields + 1 work history warning
        assert any("First name" in e for e in errors)
        assert any("Last name" in e for e in errors)
        assert any("Email address" in e for e in errors)

    def test_invalid_email(self):
        profile = UserProfile(personal_details={
            "first_name": "John",
            "last_name": "Doe",
            "email": "not-an-email",
        })
        errors = validate_user_profile(profile)
        assert any("email" in e.lower() for e in errors)

    def test_empty_work_history_warning(self):
        profile = UserProfile(
            personal_details={
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",
            },
            work_history=[],
        )
        errors = validate_user_profile(profile)
        assert any("work history" in e.lower() for e in errors)


class TestValidateFormFields:
    def test_no_issues(self):
        fields = [FormField(element_type="text", label="Name")]
        errors = validate_form_fields(fields)
        assert errors == []

    def test_hidden_required_field(self):
        fields = [FormField(element_type="hidden", required=True, label="secret")]
        errors = validate_form_fields(fields)
        assert len(errors) == 1


class TestValidateRequiredFieldsFilled:
    def test_all_filled(self):
        canonical = {
            "first_name": FormField(label="First Name", required=True),
            "email": FormField(label="Email", required=True),
        }
        values = {"first_name": "John", "email": "john@example.com"}
        errors = validate_required_fields_filled(canonical, values)
        assert errors == []

    def test_missing_required(self):
        canonical = {
            "first_name": FormField(label="First Name", required=True),
            "email": FormField(label="Email", required=True),
        }
        values = {"first_name": ""}
        errors = validate_required_fields_filled(canonical, values)
        assert len(errors) == 2

    def test_non_required_ignored(self):
        canonical = {
            "phone": FormField(label="Phone", required=False),
        }
        values = {}
        errors = validate_required_fields_filled(canonical, values)
        assert errors == []


class TestValidateFilePath:
    def test_none_path(self):
        err = validate_file_path(None)
        assert err is not None

    def test_valid_format(self):
        err = validate_file_path("/path/to/resume.pdf", allowed_formats=[".pdf", ".docx"])
        assert err is None

    def test_invalid_format(self):
        err = validate_file_path("/path/to/resume.exe", allowed_formats=[".pdf"])
        assert err is not None

    def test_empty_path(self):
        err = validate_file_path("")
        assert err is not None


class TestCheckPreconditions:
    def test_fill_no_fields_raises(self, sample_job):
        ctx = ApplicationContext(job=sample_job, form_fields=[])
        with pytest.raises(ValidationError) as exc:
            check_preconditions("fill_application", ctx)
        assert any("No form fields" in e for e in exc.value.errors)

    def test_fill_with_fields_passes(self, sample_job):
        ctx = ApplicationContext(job=sample_job, form_fields=[FormField(label="Name")])
        check_preconditions("fill_application", ctx)

    def test_upload_no_docs_raises(self, sample_job):
        ctx = ApplicationContext(job=sample_job)
        with pytest.raises(ValidationError):
            check_preconditions("upload_documents", ctx)

    def test_upload_with_resume_passes(self, sample_job):
        ctx = ApplicationContext(job=sample_job, resume_path="/tmp/resume.pdf")
        check_preconditions("upload_documents", ctx)


# ---------------------------------------------------------------------------
# FormDetector Tests
# ---------------------------------------------------------------------------


class TestFormDetector:
    @pytest.mark.asyncio
    async def test_detect_empty_page(self):
        page = make_mock_page()
        page.query_selector_all = AsyncMock(return_value=[])
        detector = FormDetector()
        fields = await detector.detect(page)
        assert fields == []

    @pytest.mark.asyncio
    async def test_detect_raises_on_catastrophic_failure(self):
        page = make_mock_page()
        page.query_selector_all = AsyncMock(side_effect=Exception("crash"))
        detector = FormDetector()
        with pytest.raises(FormDetectionError):
            await detector.detect(page)

    def test_input_type_map(self):
        # Verify key mappings
        assert FormDetector.INPUT_TYPE_MAP["text"] == "text"
        assert FormDetector.INPUT_TYPE_MAP["email"] == "text"
        assert FormDetector.INPUT_TYPE_MAP["file"] == "file"
        assert FormDetector.INPUT_TYPE_MAP["checkbox"] == "checkbox"
        assert FormDetector.INPUT_TYPE_MAP["hidden"] == "hidden"

    def test_autocomplete_map(self):
        assert FormDetector.AUTOCOMPLETE_TO_FIELD["given-name"] == "first_name"
        assert FormDetector.AUTOCOMPLETE_TO_FIELD["email"] == "email"
        assert FormDetector.AUTOCOMPLETE_TO_FIELD["tel"] == "phone"

    def test_element_role_map(self):
        assert FormDetector.ELEMENT_ROLE_MAP["textbox"] == "text"
        assert FormDetector.ELEMENT_ROLE_MAP["combobox"] == "dropdown"


# ---------------------------------------------------------------------------
# FieldMapper Tests
# ---------------------------------------------------------------------------


class TestFieldMapper:
    def test_map_email_field(self):
        field = FormField(label="Email Address", name="email", autocomplete="email")
        mapper = FieldMapper()
        result = mapper.map_fields([field])
        assert "email" in result

    def test_map_name_fields(self):
        fields = [
            FormField(label="First Name"),
            FormField(label="Last Name"),
        ]
        mapper = FieldMapper()
        result = mapper.map_fields(fields)
        assert "first_name" in result
        assert "last_name" in result

    def test_map_phone_by_label(self):
        field = FormField(label="Phone Number")
        mapper = FieldMapper()
        result = mapper.map_fields([field])
        assert "phone" in result

    def test_map_from_name_attribute(self):
        field = FormField(name="job_title", label="")
        mapper = FieldMapper()
        result = mapper.map_fields([field])
        assert "job_title" in result

    def test_map_from_autocomplete(self):
        field = FormField(autocomplete="given-name", label="", name="")
        mapper = FieldMapper()
        result = mapper.map_fields([field])
        assert "first_name" in result

    def test_unknown_field_gets_fallback_key(self):
        field = FormField(label="Random Question", name="q1")
        mapper = FieldMapper()
        result = mapper.map_fields([field])
        assert any(k.startswith("field_") for k in result)

    def test_multiple_fields_same_type(self):
        fields = [
            FormField(label="First Name"),
            FormField(label="First Name (as on passport)"),
        ]
        mapper = FieldMapper()
        result = mapper.map_fields(fields)
        # Both map to first_name; last one wins
        assert "first_name" in result

    def test_get_unmapped_fields(self):
        fields = [
            FormField(label="First Name", selector="#fname"),
            FormField(label="Some Label", selector="#unknown"),
        ]
        mapper = FieldMapper()
        canonical = mapper.map_fields(fields)
        unmapped = mapper.get_unmapped_fields(fields, canonical)
        # All fields get a fallback mapping, so unmapped should be empty
        assert len(unmapped) == 0


# ---------------------------------------------------------------------------
# FieldFiller Tests
# ---------------------------------------------------------------------------


class TestFieldFiller:
    @pytest.mark.asyncio
    async def test_fill_text_field(self):
        page = make_mock_page()
        locator = MagicMock()
        locator.fill = AsyncMock()
        page.locator = MagicMock(return_value=locator)

        field = FormField(selector="#name", element_type="text", label="Name")
        filler = FieldFiller()
        await filler.fill_field(page, field, "John")
        locator.fill.assert_called_once_with("John")

    @pytest.mark.asyncio
    async def test_skip_readonly(self):
        page = make_mock_page()
        field = FormField(selector="#name", element_type="text", readonly=True)
        filler = FieldFiller()
        await filler.fill_field(page, field, "John")
        # Should not have called fill on readonly

    @pytest.mark.asyncio
    async def test_fill_dropdown_by_label(self):
        page = make_mock_page()
        locator = MagicMock()
        locator.select_option = AsyncMock()
        page.locator = MagicMock(return_value=locator)

        field = FormField(selector="#country", element_type="dropdown", options=["US", "CA"])
        filler = FieldFiller()
        await filler.fill_field(page, field, "US")
        locator.select_option.assert_called_once_with(label="US")

    @pytest.mark.asyncio
    async def test_fill_checkbox_check(self):
        page = make_mock_page()
        locator = MagicMock()
        locator.is_checked = AsyncMock(return_value=False)
        locator.check = AsyncMock()
        page.locator = MagicMock(return_value=locator)

        field = FormField(selector="#agree", element_type="checkbox")
        filler = FieldFiller()
        await filler.fill_field(page, field, True)
        locator.check.assert_called_once()

    @pytest.mark.asyncio
    async def test_fill_checkbox_uncheck(self):
        page = make_mock_page()
        locator = MagicMock()
        locator.is_checked = AsyncMock(return_value=True)
        locator.uncheck = AsyncMock()
        page.locator = MagicMock(return_value=locator)

        field = FormField(selector="#agree", element_type="checkbox")
        filler = FieldFiller()
        await filler.fill_field(page, field, False)
        locator.uncheck.assert_called_once()

    @pytest.mark.asyncio
    async def test_fill_all_collects_errors(self):
        page = make_mock_page()
        locator = MagicMock()
        locator.fill = AsyncMock(side_effect=Exception("cannot fill"))
        page.locator = MagicMock(return_value=locator)

        canonical = {
            "first_name": FormField(selector="#fn", label="First Name", required=True),
            "last_name": FormField(selector="#ln", label="Last Name", required=True),
        }
        values = {"first_name": "John", "last_name": "Doe"}
        filler = FieldFiller()
        errors = await filler.fill_all(page, canonical, values)
        assert len(errors) == 2
        assert all(isinstance(e, FieldFillError) for e in errors)


# ---------------------------------------------------------------------------
# ResumeUploader Tests
# ---------------------------------------------------------------------------


class TestResumeUploader:
    @pytest.mark.asyncio
    async def test_upload_no_file_input_raises(self):
        page = make_mock_page()
        page.query_selector = AsyncMock(return_value=None)
        uploader = ResumeUploader()
        with pytest.raises(UploadError):
            await uploader.upload(page, "/tmp/resume.pdf")

    @pytest.mark.asyncio
    async def test_upload_file_not_found_raises(self):
        page = make_mock_page()
        page.query_selector = AsyncMock(return_value=MagicMock())
        uploader = ResumeUploader()
        with pytest.raises(UploadError):
            await uploader.upload(page, "/nonexistent/resume.pdf")

    @pytest.mark.asyncio
    async def test_upload_success_with_temp_file(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            tmp_path = f.name

        try:
            page = make_mock_page()
            file_input = MagicMock()
            page.query_selector = AsyncMock(return_value=file_input)

            file_chooser = MagicMock()
            file_chooser.set_files = AsyncMock()

            class FakeFCInfo:
                def __init__(self, chooser):
                    self._chooser = chooser

                @property
                def value(self):
                    async def get_chooser():
                        return self._chooser
                    return get_chooser()

            fc_info = FakeFCInfo(file_chooser)

            fc_ctx = MagicMock()
            fc_ctx.__aenter__ = AsyncMock(return_value=fc_info)
            fc_ctx.__aexit__ = AsyncMock()

            page.expect_file_chooser = MagicMock(return_value=fc_ctx)

            uploader = ResumeUploader()
            result = await uploader.upload(page, tmp_path)
            assert result.uploaded is True
            assert result.file_path == tmp_path
        finally:
            os.unlink(tmp_path)

    def test_unsupported_format_raises(self):
        uploader = ResumeUploader()
        with pytest.raises(UploadError) as exc:
            uploader._validate_path("/tmp/file.exe")
        assert "File not found" in str(exc.value)

    def test_supported_formats(self):
        assert ".pdf" in ResumeUploader.SUPPORTED_FORMATS
        assert ".docx" in ResumeUploader.SUPPORTED_FORMATS


# ---------------------------------------------------------------------------
# CoverLetterGenerator Tests
# ---------------------------------------------------------------------------


class TestCoverLetterGenerator:
    @pytest.mark.asyncio
    async def test_generate_template_with_company(self, sample_job):
        gen = CoverLetterGenerator()
        text = await gen.generate(sample_job, user_name="John Doe")
        assert "TestCorp" in text
        assert "Software Engineer" in text
        assert "John Doe" in text

    @pytest.mark.asyncio
    async def test_generate_template_without_company(self):
        job = JobData(
            title="Engineer",
            company=CompanyData(name=""),
            metadata=JobMetadata(source="test", source_job_id="1", job_url="https://example.com"),
        )
        gen = CoverLetterGenerator()
        text = await gen.generate(job, user_name="Jane")
        assert "the company" in text or "the position" in text

    @pytest.mark.asyncio
    async def test_generate_to_file(self, sample_job):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = CoverLetterGenerator(output_dir=tmpdir)
            path = await gen.generate_to_file(sample_job, user_name="John")
            assert os.path.exists(path)
            content = open(path).read()
            assert "TestCorp" in content

    @pytest.mark.asyncio
    async def test_fallback_on_resume_tailor_failure(self, sample_job):
        mock_tailor = MagicMock()
        mock_tailor.run = AsyncMock(side_effect=Exception("fail"))
        gen = CoverLetterGenerator()
        gen.register_resume_tailor(mock_tailor)
        text = await gen.generate(sample_job, user_name="John")
        # Should fall back to template without raising
        assert "TestCorp" in text


# ---------------------------------------------------------------------------
# QuestionAnswerer Tests
# ---------------------------------------------------------------------------


class TestQuestionAnswerer:
    @pytest.mark.asyncio
    async def test_standard_answer_map(self, sample_job, sample_profile):
        qa = QuestionAnswerer()
        answer = await qa.answer_question("Do you require visa sponsorship?", sample_job, sample_profile)
        assert "do not require" in answer

    @pytest.mark.asyncio
    async def test_standard_answer_work_authorization(self, sample_job, sample_profile):
        qa = QuestionAnswerer()
        answer = await qa.answer_question("Are you authorized to work in the US?", sample_job, sample_profile)
        assert "authorized to work" in answer.lower()

    @pytest.mark.asyncio
    async def test_profile_based_answer(self, sample_job):
        profile = UserProfile(personal_details={"phone": "+1-555-0000"})
        qa = QuestionAnswerer()
        answer = await qa.answer_question("What is your phone number?", sample_job, profile)
        assert answer == "+1-555-0000"

    @pytest.mark.asyncio
    async def test_llm_fallback(self, sample_job, sample_profile):
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value="I have 5 years of experience.")
        qa = QuestionAnswerer(llm_client=mock_llm)
        answer = await qa.answer_question("Describe your experience", sample_job, sample_profile)
        assert answer is not None

    @pytest.mark.asyncio
    async def test_safe_fallback_yes_question(self, sample_job, sample_profile):
        qa = QuestionAnswerer()
        answer = await qa.answer_question("Do you agree to the terms?", sample_job, sample_profile)
        assert answer == "Yes"

    @pytest.mark.asyncio
    async def test_safe_fallback_default(self, sample_job, sample_profile):
        qa = QuestionAnswerer()
        answer = await qa.answer_question("What is your favorite color?", sample_job, sample_profile)
        assert answer == "Prefer not to answer"

    @pytest.mark.asyncio
    async def test_answer_all(self, sample_job, sample_profile):
        qa = QuestionAnswerer()
        questions = [
            "Do you require visa sponsorship?",
            "Are you authorized to work?",
        ]
        answers = await qa.answer_all(questions, sample_job, sample_profile)
        assert len(answers) == 2
        assert "visa" in answers[questions[0]].lower()
        assert "authorized to work" in answers[questions[1]].lower()


# ---------------------------------------------------------------------------
# SubmitHandler Tests
# ---------------------------------------------------------------------------


class TestSubmitHandler:
    @pytest.mark.asyncio
    async def test_review_mode(self):
        page = make_mock_page()
        handler = SubmitHandler()
        result = await handler.execute(page, mode="review")
        assert result["submitted"] is False
        assert result["confirmation_code"] is None

    @pytest.mark.asyncio
    async def test_dry_run_mode(self):
        page = make_mock_page()
        handler = SubmitHandler()
        result = await handler.execute(page, mode="dry_run")
        assert result["submitted"] is False

    @pytest.mark.asyncio
    async def test_submit_no_button_raises(self):
        page = make_mock_page()
        # Mock find_submit_button to return None
        handler = SubmitHandler()
        with patch.object(handler, "_find_submit_button", AsyncMock(return_value=None)):
            with pytest.raises(SubmissionError):
                await handler.execute(page, mode="submit")

    @pytest.mark.asyncio
    async def test_submit_success(self):
        page = make_mock_page()
        mock_button = MagicMock()
        mock_button.click = AsyncMock()
        handler = SubmitHandler()

        with patch.object(handler, "_find_submit_button", AsyncMock(return_value=mock_button)):
            with patch.object(handler, "_verify_submission", AsyncMock(return_value="CONF-123")):
                with patch.object(handler, "_detect_error", AsyncMock(return_value=False)):
                    result = await handler.execute(page, mode="submit")
                    assert result["submitted"] is True
                    assert result["confirmation_code"] == "CONF-123"

    @pytest.mark.asyncio
    async def test_submit_error_detected_after_submission(self):
        page = make_mock_page()
        mock_button = MagicMock()
        handler = SubmitHandler()

        with patch.object(handler, "_find_submit_button", AsyncMock(return_value=mock_button)):
            with patch.object(handler, "_detect_error", AsyncMock(return_value=True)):
                with pytest.raises(SubmissionError):
                    await handler.execute(page, mode="submit")

    @pytest.mark.asyncio
    async def test_confirmation_patterns(self):
        handler = SubmitHandler()
        assert any("thank you" in p for p in handler.CONFIRMATION_PATTERNS)
        assert any("submitted" in p for p in handler.CONFIRMATION_PATTERNS)

    @pytest.mark.asyncio
    async def test_unknown_mode_raises(self):
        page = make_mock_page()
        handler = SubmitHandler()
        with pytest.raises(SubmissionError):
            await handler.execute(page, mode="invalid")


# ---------------------------------------------------------------------------
# ApplyAgent Integration Tests (mock-based)
# ---------------------------------------------------------------------------


class TestApplyAgent:
    @pytest.mark.asyncio
    async def test_apply_agent_run_review_mode(self, sample_job, sample_profile):
        mock_browser = make_mock_browser_session()
        agent = ApplyAgent(browser_session=mock_browser, logger=None)
        input_data = ApplyAgentInput(
            job=sample_job,
            application_url="https://example.com/apply",
            user_profile=sample_profile,
            config=ApplyAgentConfig(mode="review"),
        )
        result = await agent.run(input_data)
        assert isinstance(result, ApplicationResult)
        # Should not raise; review mode completes without submission

    @pytest.mark.asyncio
    async def test_apply_agent_run_dry_run(self, sample_job, sample_profile):
        mock_browser = make_mock_browser_session()
        agent = ApplyAgent(browser_session=mock_browser)
        input_data = ApplyAgentInput(
            job=sample_job,
            application_url="https://example.com/apply",
            user_profile=sample_profile,
            config=ApplyAgentConfig(mode="dry_run"),
        )
        result = await agent.run(input_data)
        assert isinstance(result, ApplicationResult)

    @pytest.mark.asyncio
    async def test_apply_agent_navigation_failure(self, sample_job, sample_profile):
        mock_browser = make_mock_browser_session()
        mock_browser.navigate = AsyncMock(side_effect=Exception("timeout"))
        agent = ApplyAgent(browser_session=mock_browser)
        input_data = ApplyAgentInput(
            job=sample_job,
            application_url="https://example.com/apply",
            user_profile=sample_profile,
            config=ApplyAgentConfig(mode="review"),
        )
        result = await agent.run(input_data)
        assert result.success is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_register_agents(self):
        mock_browser = make_mock_browser_session()
        agent = ApplyAgent(browser_session=mock_browser)
        mock_tailor = MagicMock()
        mock_jd = MagicMock()
        agent.register_resume_tailor(mock_tailor)
        agent.register_jd_analyzer(mock_jd)
        assert agent._resume_tailor is mock_tailor
        assert agent._jd_analyzer is mock_jd

    @pytest.mark.asyncio
    async def test_cover_letter_generation_enabled(self, sample_job, sample_profile):
        mock_browser = make_mock_browser_session()
        agent = ApplyAgent(browser_session=mock_browser)
        input_data = ApplyAgentInput(
            job=sample_job,
            application_url="https://example.com/apply",
            user_profile=sample_profile,
            config=ApplyAgentConfig(mode="review", generate_cover_letter=True),
        )
        result = await agent.run(input_data)
        assert isinstance(result, ApplicationResult)

    def test_build_context(self, sample_job, sample_profile):
        agent = ApplyAgent(browser_session=make_mock_browser_session())
        input_data = ApplyAgentInput(
            job=sample_job,
            application_url="https://example.com/apply",
            user_profile=sample_profile,
            config=ApplyAgentConfig(mode="review", generate_cover_letter=True),
        )
        ctx = agent._build_context(input_data)
        assert ctx.job.title == "Software Engineer"
        assert ctx.mode == "review"
        assert ctx.resume_path is None

    def test_build_field_values(self, sample_job, sample_profile):
        agent = ApplyAgent(browser_session=make_mock_browser_session())
        ctx = agent._build_context(
            ApplyAgentInput(
                job=sample_job,
                application_url="https://example.com/apply",
                user_profile=sample_profile,
            )
        )
        ctx.canonical_fields = {"first_name": FormField(label="First Name")}
        values = agent._build_field_values(ctx)
        assert values.get("first_name") == "John"
