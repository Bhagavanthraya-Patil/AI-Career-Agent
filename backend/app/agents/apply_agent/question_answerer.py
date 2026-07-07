from __future__ import annotations

from typing import Any, Optional

from app.agents.apply_agent.exceptions import ApplyError
from app.collectors.logging import CollectorLoggerProtocol
from app.collectors.models import JobData


class QuestionAnswerer:
    """Answers application-specific questions found on the form.

    For standard questions (work authorization, veteran status, etc.),
    uses the user profile. For non-standard questions, delegates to
    the JD Analyzer agent or falls back to rule-based answers.

    Usage::

        qa = QuestionAnswerer(llm_client=llm, logger=logger)
        answers = await qa.answer_all(page, context)
    """

    STANDARD_ANSWER_MAP: dict[str, str] = {
        "visa_sponsorship": "No, I do not require visa sponsorship",
        "work_authorization": "Yes, I am authorized to work in the United States",
        "relocation": "Yes, I am willing to relocate",
        "gender": "Prefer not to say",
        "race_ethnicity": "Prefer not to say",
        "veteran": "I am not a protected veteran",
        "disability": "No, I do not have a disability",
        "eeo_self_identify": "Prefer not to answer",
    }

    def __init__(
        self,
        llm_client: Optional[Any] = None,
        logger: Optional[CollectorLoggerProtocol] = None,
    ) -> None:
        self._llm = llm_client
        self._logger = logger
        self._jd_analyzer = None

    def register_jd_analyzer(self, jd_analyzer: Any) -> None:
        """Register a JDAnalyzerAgent instance for AI question answering."""
        self._jd_analyzer = jd_analyzer

    def _log(self, message: str, level: str = "info") -> None:
        if self._logger:
            getattr(self._logger, level, print)(message)

    async def answer_question(self, question_text: str, job: JobData, profile: Any) -> str:
        """Answer a single question based on context.

        Strategy:
        1. Check standard answer map for known question types.
        2. Check user profile for a direct answer.
        3. Use JD Analyzer if registered.
        4. Fall back to LLM-based answer.
        5. Final fallback: rule-based safe answer.

        Args:
            question_text: The question text from the form.
            job: The job data for context.
            profile: The UserProfile for personal data.

        Returns:
            The answer string.

        Raises:
            ApplyError: If all strategies fail.
        """
        canonical_type = self._classify_question(question_text)

        # Strategy 1: Standard answer map
        if canonical_type in self.STANDARD_ANSWER_MAP:
            return self.STANDARD_ANSWER_MAP[canonical_type]

        # Strategy 2: User profile
        profile_answer = self._check_profile(question_text, canonical_type, profile)
        if profile_answer:
            return profile_answer

        # Strategy 3: JD Analyzer
        if self._jd_analyzer is not None:
            try:
                answer = await self._answer_via_jd_analyzer(question_text, job)
                if answer:
                    return answer
            except Exception:
                pass

        # Strategy 4: LLM fallback
        if self._llm is not None:
            try:
                answer = await self._answer_via_llm(question_text, job)
                if answer:
                    return answer
            except Exception as exc:
                self._log(f"LLM question answering failed: {exc}", "warning")

        # Strategy 5: Safe fallback
        return self._safe_fallback(question_text)

    async def answer_all(
        self,
        questions: list[str],
        job: JobData,
        profile: Any,
    ) -> dict[str, str]:
        """Answer multiple questions.

        Returns a dict mapping question text to answer.
        """
        answers: dict[str, str] = {}
        for q in questions:
            answer = await self.answer_question(q, job, profile)
            answers[q] = answer
        return answers

    def _classify_question(self, question: str) -> str:
        """Classify a question into a canonical type."""
        from app.agents.apply_agent.field_mapper import FieldMapper
        from app.agents.apply_agent.application_context import FormField

        mapper = FieldMapper()
        # Create a temporary FormField to use the mapper's pattern matching
        temp_field = FormField(label=question)
        result = mapper._match_canonical(temp_field)
        return result or "unknown"

    def _check_profile(self, question: str, canonical_type: str, profile: Any) -> Optional[str]:
        """Check the user profile for a direct answer."""
        if canonical_type and canonical_type != "unknown":
            details = getattr(profile, "personal_details", {})
            if canonical_type in details:
                val = details[canonical_type]
                if val is not None:
                    return str(val)
        return None

    async def _answer_via_jd_analyzer(self, question: str, job: JobData) -> Optional[str]:
        """Use JD Analyzer to answer a question based on the job description."""
        try:
            from app.agents.jd_analyzer.agent import JDAnalyzerAgent

            analyzer = self._jd_analyzer
            if isinstance(analyzer, JDAnalyzerAgent):
                result = await analyzer.analyze(job.description_raw or "")
                analysis = result.to_dict() if hasattr(result, "to_dict") else {}

                for key, value in analysis.items():
                    if isinstance(value, str) and question.lower() in key.lower():
                        return value
        except Exception:
            pass
        return None

    async def _answer_via_llm(self, question: str, job: JobData) -> Optional[str]:
        """Use the LLM client to generate a contextual answer."""
        prompt = (
            f"Job Title: {job.title}\n"
            f"Company: {job.company.name if job.company else 'Unknown'}\n"
            f"Job Description: {job.description_raw[:1000] if job.description_raw else 'N/A'}\n\n"
            f"Question: {question}\n\n"
            f"Provide a brief, professional answer to this application question."
        )
        response = await self._llm.generate(prompt)
        return response.strip() if response else None

    def _safe_fallback(self, question: str) -> str:
        """Provide a safe default answer when all strategies fail."""
        question_lower = question.lower()
        if any(word in question_lower for word in ["yes", "agree", "consent", "accept"]):
            return "Yes"
        if any(word in question_lower for word in ["no", "not"]):
            return "No"
        return "Prefer not to answer"
