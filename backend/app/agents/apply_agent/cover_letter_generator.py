from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.agents.apply_agent.exceptions import ApplyError
from app.collectors.logging import CollectorLoggerProtocol
from app.collectors.models import JobData


class CoverLetterGenerator:
    """Generates or retrieves a cover letter for a job application.

    If the Resume Tailor agent is available, delegates to it for
    AI-powered cover letter generation. Otherwise, falls back to
    a template-based approach.

    Usage::

        cl_generator = CoverLetterGenerator(logger=logger)
        result = await cl_generator.generate(job_data, user_name="John Doe")
    """

    def __init__(
        self,
        output_dir: Optional[str] = None,
        logger: Optional[CollectorLoggerProtocol] = None,
    ) -> None:
        self._output_dir = output_dir
        self._logger = logger
        self._resume_tailor = None

    def register_resume_tailor(self, resume_tailor: Any) -> None:
        """Register a ResumeTailorAgent instance for AI generation."""
        self._resume_tailor = resume_tailor

    def _log(self, message: str, level: str = "info") -> None:
        if self._logger:
            getattr(self._logger, level, print)(message)

    async def generate(
        self,
        job: JobData,
        user_name: str = "",
        additional_context: Optional[str] = None,
    ) -> str:
        """Generate a cover letter for the given job.

        Args:
            job: The job data to generate a cover letter for.
            user_name: The applicant's name for the signature.
            additional_context: Any extra context for the generation.

        Returns:
            The generated cover letter text.

        Raises:
            ApplyError: If generation fails.
        """
        if self._resume_tailor is not None:
            return await self._generate_via_resume_tailor(job, additional_context)
        return self._generate_template(job, user_name)

    async def generate_to_file(
        self,
        job: JobData,
        user_name: str = "",
        additional_context: Optional[str] = None,
        output_path: Optional[str] = None,
    ) -> str:
        """Generate a cover letter and write it to a file.

        Returns the file path.
        """
        text = await self.generate(job, user_name, additional_context)
        path = output_path or self._default_output_path(job)
        Path(path).write_text(text, encoding="utf-8")
        self._log(f"Cover letter written to {path}")
        return path

    async def _generate_via_resume_tailor(self, job: JobData, additional_context: Optional[str] = None) -> str:
        """Delegate cover letter generation to ResumeTailorAgent."""
        try:
            from app.agents.resume_tailor.agent import ResumeTailorAgent as RTA

            if isinstance(self._resume_tailor, RTA):
                result = await self._resume_tailor.run(
                    job.description_raw or "",
                    additional_context=additional_context or "",
                    output_format="cover_letter",
                )
                if hasattr(result, "cover_letter") and result.cover_letter:
                    return result.cover_letter
                if hasattr(result, "tailored_resume") and result.tailored_resume:
                    return result.tailored_resume
                return str(result)
        except ImportError:
            self._log("ResumeTailorAgent not available; using template", "warning")
        except Exception as exc:
            self._log(f"ResumeTailorAgent failed: {exc}; using template", "warning")
        return self._generate_template(job, "")

    def _generate_template(self, job: JobData, user_name: str) -> str:
        """Generate a simple template-based cover letter."""
        company = job.company.name if job.company and job.company.name else "the company"
        title = job.title or "the position"
        lines = [
            f"Dear Hiring Team at {company},",
            "",
            f"I am writing to express my strong interest in the {title} position.",
        ]
        if job.description_raw:
            lines.append("")
            lines.append("After reviewing the job description, I am confident that my skills")
            lines.append("and experience align well with the requirements of this role.")
        lines.append("")
        lines.append("I look forward to the opportunity to discuss how I can contribute")
        lines.append(f"to the success of {company}.")
        lines.append("")
        lines.append("Best regards,")
        if user_name:
            lines.append(user_name)
        return "\n".join(lines)

    def _default_output_path(self, job: JobData) -> str:
        """Generate a default output path for the cover letter."""
        company_name = job.company.name if job.company else "unknown"
        safe_company = "".join(c if c.isalnum() or c in " _-" else "_" for c in company_name)
        dir_path = self._output_dir or "."
        return str(Path(dir_path) / f"cover_letter_{safe_company}.txt")
