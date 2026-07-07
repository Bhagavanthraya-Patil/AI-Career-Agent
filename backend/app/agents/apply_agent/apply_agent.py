from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional

from app.agents.apply_agent.application_context import ApplicationContext, FormField, UserProfile
from app.agents.apply_agent.application_result import ApplicationResult
from app.agents.apply_agent.application_session import ApplicationSession
from app.agents.apply_agent.cover_letter_generator import CoverLetterGenerator
from app.agents.apply_agent.exceptions import (
    ApplyError,
    FormDetectionError,
    StateTransitionError,
    ValidationError,
)
from app.agents.apply_agent.field_fillers import FieldFiller
from app.agents.apply_agent.field_mapper import FieldMapper
from app.agents.apply_agent.form_detector import FormDetector
from app.agents.apply_agent.question_answerer import QuestionAnswerer
from app.agents.apply_agent.resume_uploader import ResumeUploader
from app.agents.apply_agent.state_machine import ApplicationState
from app.agents.apply_agent.submit_handler import SubmitHandler
from app.agents.apply_agent.validation import check_preconditions
from app.collectors.logging import CollectorLoggerProtocol
from app.collectors.models import JobData


@dataclass
class ApplyAgentConfig:
    """Configuration for the ApplyAgent orchestrator."""

    mode: str = "review"
    screenshot_dir: Optional[str] = None
    storage_path: Optional[str] = None
    navigation_timeout: int = 30000
    generate_cover_letter: bool = False
    max_retries: int = 2
    headless: bool = True


@dataclass
class ApplyAgentInput:
    """Input for a single application run."""

    job: JobData
    application_url: str
    user_profile: UserProfile = field(default_factory=UserProfile)
    resume_path: Optional[str] = None
    cover_letter_path: Optional[str] = None
    additional_context: Optional[str] = None
    config: ApplyAgentConfig = field(default_factory=ApplyAgentConfig)


class ApplyAgent:
    """Primary orchestrator for the job application automation.

    Composes all sub-components (navigation, form detection, field
    filling, document upload, cover letter generation, question
    answering, submission) into a single lifecycle driven by a
    state machine.

    Usage::

        agent = ApplyAgent(browser_session=browser, logger=logger)
        result = await agent.run(input_data)
        print(result.summary)
    """

    def __init__(
        self,
        browser_session: Any,
        llm_client: Optional[Any] = None,
        logger: Optional[CollectorLoggerProtocol] = None,
    ) -> None:
        self._browser_session = browser_session
        self._llm_client = llm_client
        self._logger = logger

        # Sub-components (lazy init or injected)
        self._form_detector: Optional[FormDetector] = None
        self._field_mapper: Optional[FieldMapper] = None
        self._field_filler: Optional[FieldFiller] = None
        self._resume_uploader: Optional[ResumeUploader] = None
        self._cover_letter_generator: Optional[CoverLetterGenerator] = None
        self._question_answerer: Optional[QuestionAnswerer] = None
        self._submit_handler: Optional[SubmitHandler] = None

        # External agent references (optional injection)
        self._resume_tailor: Any = None
        self._jd_analyzer: Any = None

    def _log(self, message: str, level: str = "info") -> None:
        if self._logger:
            getattr(self._logger, level, print)(message)

    def register_resume_tailor(self, resume_tailor: Any) -> None:
        """Register a ResumeTailorAgent for cover letter generation."""
        self._resume_tailor = resume_tailor

    def register_jd_analyzer(self, jd_analyzer: Any) -> None:
        """Register a JDAnalyzerAgent for question answering."""
        self._jd_analyzer = jd_analyzer

    # --- Component initialization ---

    def _get_form_detector(self) -> FormDetector:
        if self._form_detector is None:
            self._form_detector = FormDetector(logger=self._logger)
        return self._form_detector

    def _get_field_mapper(self) -> FieldMapper:
        if self._field_mapper is None:
            self._field_mapper = FieldMapper()
        return self._field_mapper

    def _get_field_filler(self) -> FieldFiller:
        if self._field_filler is None:
            self._field_filler = FieldFiller(logger=self._logger)
        return self._field_filler

    def _get_resume_uploader(self, config: ApplyAgentConfig) -> ResumeUploader:
        if self._resume_uploader is None:
            self._resume_uploader = ResumeUploader(
                storage_path=config.storage_path,
                logger=self._logger,
            )
        return self._resume_uploader

    def _get_cover_letter_generator(self, config: ApplyAgentConfig) -> CoverLetterGenerator:
        if self._cover_letter_generator is None:
            gen = CoverLetterGenerator(
                output_dir=config.screenshot_dir,
                logger=self._logger,
            )
            if self._resume_tailor is not None:
                gen.register_resume_tailor(self._resume_tailor)
            self._cover_letter_generator = gen
        return self._cover_letter_generator

    def _get_question_answerer(self) -> QuestionAnswerer:
        if self._question_answerer is None:
            qa = QuestionAnswerer(
                llm_client=self._llm_client,
                logger=self._logger,
            )
            if self._jd_analyzer is not None:
                qa.register_jd_analyzer(self._jd_analyzer)
            self._question_answerer = qa
        return self._question_answerer

    def _get_submit_handler(self, config: ApplyAgentConfig) -> SubmitHandler:
        if self._submit_handler is None:
            self._submit_handler = SubmitHandler(
                screenshot_dir=config.screenshot_dir,
                logger=self._logger,
            )
        return self._submit_handler

    # --- Lifecycle ---

    async def run(self, input_data: ApplyAgentInput) -> ApplicationResult:
        """Execute the full application lifecycle.

        Args:
            input_data: The application input with job, profile, and config.

        Returns:
            An ApplicationResult with the outcome.
        """
        start_time = time.monotonic()
        ctx = self._build_context(input_data)
        result = ApplicationResult(job=input_data.job)

        try:
            await self._lifecycle(ctx, input_data)
            result.success = ctx.state in (
                ApplicationState.VERIFIED,
                ApplicationState.REVIEWED,
            )
            result.final_state = ctx.state
            result.screenshot_path = ctx.submit_screenshot or (
                ctx.review_screenshots[-1] if ctx.review_screenshots else None
            )
            result.confirmation_code = ctx.confirmation_code
            result.errors = list(ctx.errors)
            result.review_screenshots = list(ctx.review_screenshots)
            result.state_history = [
                (prev.value, curr.value, reason)
                for prev, curr, reason in ctx.state_machine.history
            ]

        except Exception as exc:
            self._log(f"Application failed: {exc}", "error")
            ctx.add_error(str(exc))
            result.success = False
            result.final_state = ctx.state
            result.errors = list(ctx.errors)
            result.state_history = [
                (prev.value, curr.value, reason)
                for prev, curr, reason in ctx.state_machine.history
            ]
            await self._safe_cleanup(ctx)

        finally:
            result.duration_seconds = time.monotonic() - start_time

        return result

    def _build_context(self, input_data: ApplyAgentInput) -> ApplicationContext:
        """Build the initial application context from input."""
        return ApplicationContext(
            job=input_data.job,
            user_profile=input_data.user_profile,
            resume_path=input_data.resume_path,
            cover_letter_path=input_data.cover_letter_path,
            mode=input_data.config.mode,
        )

    async def _lifecycle(self, ctx: ApplicationContext, input_data: ApplyAgentInput) -> None:
        """Run the application lifecycle step by step."""
        session = ApplicationSession(
            browser_session=self._browser_session,
            logger=self._logger,
        )
        ctx.session_ref = session

        # Step 1: Navigate
        await self._step_navigate(ctx, input_data, session)

        # Step 2: Analyze page
        await self._step_analyze(ctx, session)

        # Step 3: Fill fields
        await self._step_fill(ctx, session)

        # Step 4: Upload documents
        await self._step_upload(ctx, input_data, session)

        # Step 5: Generate cover letter (if configured)
        if input_data.config.generate_cover_letter and not ctx.cover_letter_path:
            await self._step_cover_letter(ctx, input_data)

        # Step 6: Answer questions
        await self._step_questions(ctx, input_data, session)

        # Step 7: Submit / review
        await self._step_submit(ctx, input_data, session)

        # Step 8: Verify
        if ctx.mode == "submit":
            await self._step_verify(ctx, session)

        await self._safe_cleanup(ctx)

    async def _step_navigate(
        self,
        ctx: ApplicationContext,
        input_data: ApplyAgentInput,
        session: ApplicationSession,
    ) -> None:
        """Navigate to the application URL."""
        self._log(f"Navigating to {input_data.application_url}")
        await session.navigate(
            url=input_data.application_url,
            timeout=input_data.config.navigation_timeout,
        )
        ctx.state_machine.transition_to(ApplicationState.PAGE_LOADED)

    async def _step_analyze(self, ctx: ApplicationContext, session: ApplicationSession) -> None:
        """Detect and map form fields."""
        self._log("Analyzing page for form fields")
        page = session.current_page
        detector = self._get_form_detector()
        mapper = self._get_field_mapper()

        fields = await detector.detect(page)
        if not fields:
            raise FormDetectionError(
                message="No form fields detected on the page",
                step="analyze",
            )

        ctx.form_fields = fields
        ctx.canonical_fields = mapper.map_fields(fields)
        ctx.state_machine.transition_to(ApplicationState.ANALYZED)

        mapped_count = len(ctx.canonical_fields)
        self._log(f"Mapped {mapped_count} canonical fields from {len(fields)} detected fields")

    async def _step_fill(self, ctx: ApplicationContext, session: ApplicationSession) -> None:
        """Fill all mapped form fields with user profile data."""
        check_preconditions("fill_application", ctx)
        self._log("Filling form fields")

        page = session.current_page
        filler = self._get_field_filler()
        values = self._build_field_values(ctx)
        ctx.field_values = values

        errors = await filler.fill_all(page, ctx.canonical_fields, values)
        for err in errors:
            ctx.add_error(str(err))

        ctx.state_machine.transition_to(ApplicationState.FILLED)

        # Capture review screenshot
        screenshot = await session.screenshot()
        if screenshot:
            ctx.review_screenshots.append(screenshot)

    async def _step_upload(
        self,
        ctx: ApplicationContext,
        input_data: ApplyAgentInput,
        session: ApplicationSession,
    ) -> None:
        """Upload resume and any additional documents."""
        page = session.current_page
        uploader = self._get_resume_uploader(input_data.config)

        if ctx.resume_path:
            self._log(f"Uploading resume: {ctx.resume_path}")
            doc = await uploader.upload(page, ctx.resume_path)
            ctx.uploaded_documents.append(doc)
            if not doc.uploaded and doc.error:
                ctx.add_error(doc.error)

        if ctx.cover_letter_path:
            self._log(f"Uploading cover letter: {ctx.cover_letter_path}")
            doc = await uploader.upload(page, ctx.cover_letter_path)
            ctx.uploaded_documents.append(doc)
            if not doc.uploaded and doc.error:
                ctx.add_error(doc.error)

        ctx.state_machine.transition_to(ApplicationState.UPLOADED)

    async def _step_cover_letter(
        self,
        ctx: ApplicationContext,
        input_data: ApplyAgentInput,
    ) -> None:
        """Generate a cover letter if not already provided."""
        self._log("Generating cover letter")
        generator = self._get_cover_letter_generator(input_data.config)
        user_name = ctx.user_profile.personal_details.get("full_name", "")
        path = await generator.generate_to_file(
            job=ctx.job,
            user_name=user_name,
            additional_context=input_data.additional_context,
        )
        ctx.cover_letter_path = path
        self._log(f"Cover letter generated at {path}")

    async def _step_questions(
        self,
        ctx: ApplicationContext,
        input_data: ApplyAgentInput,
        session: ApplicationSession,
    ) -> None:
        """Answer any non-standard questions on the form."""
        if not ctx.detected_questions:
            return

        self._log(f"Answering {len(ctx.detected_questions)} questions")
        qa = self._get_question_answerer()
        answers = await qa.answer_all(
            questions=ctx.detected_questions,
            job=ctx.job,
            profile=ctx.user_profile,
        )
        ctx.answered_questions = answers
        self._log(f"Answered {len(answers)} questions")

    async def _step_submit(
        self,
        ctx: ApplicationContext,
        input_data: ApplyAgentInput,
        session: ApplicationSession,
    ) -> None:
        """Execute submission (review, dry-run, or actual submit)."""
        check_preconditions("submit", ctx)
        self._log(f"Executing submission in mode: {ctx.mode}")

        page = session.current_page
        handler = self._get_submit_handler(input_data.config)
        submit_result = await handler.execute(page, mode=ctx.mode)

        if submit_result.get("screenshot"):
            ctx.submit_screenshot = submit_result["screenshot"]

        if submit_result.get("confirmation_code"):
            ctx.confirmation_code = submit_result["confirmation_code"]

        if submit_result.get("errors"):
            for err in submit_result["errors"]:
                ctx.add_error(err)

        ctx.state_machine.transition_to(ApplicationState.REVIEWED)

    async def _step_verify(self, ctx: ApplicationContext, session: ApplicationSession) -> None:
        """Verify that the submission was successful."""
        if ctx.confirmation_code:
            ctx.state_machine.transition_to(ApplicationState.VERIFIED)
        else:
            self._log("No confirmation code detected; submission may not have completed", "warning")
            ctx.state_machine.transition_to(ApplicationState.SUBMITTED)

    async def _safe_cleanup(self, ctx: ApplicationContext) -> None:
        """Safely close the browser session, swallowing cleanup errors."""
        session: Optional[ApplicationSession] = ctx.session_ref
        if session is not None and not session.is_closed:
            try:
                await session.close()
            except Exception as exc:
                self._log(f"Cleanup error (swallowed): {exc}", "warning")

    def _build_field_values(self, ctx: ApplicationContext) -> dict[str, Any]:
        """Build a mapping of canonical field type to value from the user profile."""
        values: dict[str, Any] = {}
        profile = ctx.user_profile
        details = profile.personal_details

        for canon in ctx.canonical_fields:
            if canon in details:
                values[canon] = details[canon]

        return values
