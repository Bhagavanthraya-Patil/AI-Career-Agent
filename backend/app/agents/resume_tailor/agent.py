from __future__ import annotations

import re
from typing import Optional

from app.agents.llm import LLMClient
from app.agents.resume_tailor.models import (
    Education,
    Project,
    ResumeTailorInput,
    ResumeTailorOutput,
    TailoredBullet,
    UserProfile,
    WorkExperience,
)
from app.collectors.logging import CollectorLoggerProtocol


class ResumeTailorAgent:
    """Tailor a candidate's resume to match a target job description.

    Rewrites bullet points to mirror JD terminology, re-orders and
    emphasizes relevant skills, and generates a complete ATS-friendly
    markdown resume.
    """

    SYSTEM_PROMPT = """You are a Resume Tailoring Expert. Your job is to rewrite a candidate's work experience to align with a target job description.

For each bullet point:
1. Analyze what the original bullet communicates
2. Rewrite it using terminology from the target JD while keeping the original meaning and factual accuracy
3. Use strong action verbs and measurable outcomes where possible
4. Incorporate relevant keywords from the JD naturally

Return your response as valid JSON with this schema:
{
  "tailored_bullets": [
    {
      "original": str,
      "tailored": str,
      "matched_keywords": [str]
    }
  ],
  "reordered_skills": [str],
  "summary_statement": str,
  "missing_skills": [str]
}"""

    ACTION_VERBS = [
        "Achieved", "Built", "Championed", "Created", "Decreased", "Delivered",
        "Designed", "Developed", "Drove", "Eliminated", "Engineered", "Established",
        "Generated", "Grew", "Implemented", "Improved", "Increased", "Initiated",
        "Integrated", "Introduced", "Launched", "Led", "Managed", "Optimized",
        "Orchestrated", "Pioneered", "Proposed", "Rebuilt", "Reduced", "Redesigned",
        "Resolved", "Revamped", "Scaled", "Simplified", "Spearheaded", "Standardized",
        "Streamlined", "Strengthened", "Transformed", "Upgraded",
    ]

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        logger: Optional[CollectorLoggerProtocol] = None,
    ) -> None:
        self._llm = llm_client
        self._logger = logger

    async def run(self, input_data: ResumeTailorInput) -> ResumeTailorOutput:
        if not input_data.user_profile or not input_data.target_skills:
            profile = input_data.user_profile or UserProfile(name="", title="")
            return ResumeTailorOutput(
                reordered_skills=profile.skills,
                summary_statement=profile.summary,
            )

        if self._llm is not None and self._llm.provider is not None:
            try:
                return await self._tailor_with_llm(input_data)
            except Exception as e:
                if self._logger:
                    self._logger.warning(
                        f"LLM resume tailoring failed, falling back to keyword-based: {e}"
                    )

        return self._tailor_with_keywords(input_data)

    def _build_llm_prompt(self, input_data: ResumeTailorInput) -> str:
        profile = input_data.user_profile
        lines = [
            "Tailor the following candidate profile to match the target job requirements.",
            "",
            "## Candidate Profile",
            f"Name: {profile.name}",
            f"Current Title: {profile.title}",
            f"Summary: {profile.summary}",
            "",
            "### Skills",
        ]
        for s in profile.skills:
            lines.append(f"- {s}")

        lines.append("")
        lines.append("### Work Experience")
        for exp in profile.experience:
            lines.append(f"**{exp.title} at {exp.company}** ({exp.start_date} - {exp.end_date or 'Present'})")
            for b in exp.bullets:
                lines.append(f"  - {b}")

        lines.append("")
        lines.append("### Education")
        for edu in profile.education:
            lines.append(f"- {edu.degree} in {edu.field}, {edu.institution} ({edu.year})")

        if profile.projects:
            lines.append("")
            lines.append("### Projects")
            for proj in profile.projects:
                lines.append(f"- {proj.name}: {proj.description} ({', '.join(proj.technologies)})")

        lines.extend([
            "",
            "## Target Job Requirements",
            f"Role: {input_data.target_role or 'N/A'}",
            f"JD Summary: {input_data.jd_summary or 'N/A'}",
            "Target Skills: " + ", ".join(input_data.target_skills),
            "Target Keywords: " + ", ".join(input_data.target_keywords),
            "Key Responsibilities:",
        ])
        for r in input_data.target_responsibilities:
            lines.append(f"- {r}")

        lines.append("")
        lines.append("Produce tailored bullet points, reordered skills, a summary statement, and identify missing skills.")

        return "\n".join(lines)

    async def _tailor_with_llm(self, input_data: ResumeTailorInput) -> ResumeTailorOutput:
        prompt = self._build_llm_prompt(input_data)
        result = await self._llm.generate_structured(
            prompt=prompt,
            system_prompt=self.SYSTEM_PROMPT,
        )

        return self._parse_llm_response(result, input_data)

    def _parse_llm_response(
        self,
        result: dict,
        input_data: ResumeTailorInput,
    ) -> ResumeTailorOutput:
        bullets_raw = result.get("tailored_bullets", [])
        bullets = [
            TailoredBullet(
                original=b.get("original", ""),
                tailored=b.get("tailored", ""),
                matched_keywords=b.get("matched_keywords", []),
            )
            for b in bullets_raw
        ]

        reordered = result.get("reordered_skills", [])
        summary = result.get("summary_statement", input_data.user_profile.summary)
        missing = result.get("missing_skills", [])

        markdown = self._build_markdown(
            input_data.user_profile,
            bullets,
            reordered,
            summary,
        )

        return ResumeTailorOutput(
            tailored_bullets=bullets,
            reordered_skills=reordered,
            summary_statement=summary,
            markdown_resume=markdown,
            missing_skills=missing,
        )

    def _tailor_with_keywords(self, input_data: ResumeTailorInput) -> ResumeTailorOutput:
        profile = input_data.user_profile
        target_skills = set(s.lower() for s in input_data.target_skills)
        target_keywords = set(k.lower() for k in input_data.target_keywords)

        bullets = []
        for exp in profile.experience:
            for b in exp.bullets:
                matched = self._find_matched_keywords(b, target_keywords, target_skills)
                tailored = self._tailor_bullet(b, matched)
                bullets.append(TailoredBullet(
                    original=b,
                    tailored=tailored,
                    matched_keywords=list(matched),
                ))

        reordered = self._reorder_skills(profile.skills, target_skills)
        skills_lower = set(s.lower() for s in profile.skills)
        missing = [s for s in input_data.target_skills if s.lower() not in skills_lower]

        summary = self._tailor_summary(profile.summary, input_data.target_role, target_skills)
        markdown = self._build_markdown(profile, bullets, reordered, summary)

        return ResumeTailorOutput(
            tailored_bullets=bullets,
            reordered_skills=reordered,
            summary_statement=summary,
            markdown_resume=markdown,
            missing_skills=missing,
        )

    def _find_matched_keywords(
        self,
        text: str,
        target_keywords: set[str],
        target_skills: set[str],
    ) -> set[str]:
        matched: set[str] = set()
        lower = text.lower()
        for kw in target_keywords | target_skills:
            if kw in lower:
                matched.add(kw)
        return matched

    def _tailor_bullet(self, bullet: str, matched_keywords: set[str]) -> str:
        tailored = bullet.strip()

        if not tailored:
            return tailored

        has_action = any(
            tailored.lower().startswith(verb.lower())
            for verb in self.ACTION_VERBS
        )
        if not has_action:
            for verb in self.ACTION_VERBS:
                if verb.lower() in tailored.lower():
                    has_action = True
                    break

        if not has_action:
            for verb in self.ACTION_VERBS[:10]:
                if matched_keywords:
                    keyword_hint = next(iter(matched_keywords)).title()
                    tailored = f"{verb} {tailored[0].lower()}{tailored[1:]}"
                    break

        for kw in matched_keywords:
            if kw.lower() not in tailored.lower():
                tailored = tailored.rstrip(".")
                tailored += f" (utilizing {kw})"

        return tailored

    def _reorder_skills(self, skills: list[str], target_skills: set[str]) -> list[str]:
        matched = [s for s in skills if s.lower() in target_skills]
        unmatched = [s for s in skills if s.lower() not in target_skills]
        return matched + unmatched

    def _tailor_summary(
        self,
        original: str,
        target_role: Optional[str],
        target_skills: set[str],
    ) -> str:
        if not original and target_role:
            skill_hint = list(target_skills)[:3]
            return (
                f"Experienced {target_role} professional with expertise in "
                f"{', '.join(skill_hint)}. "
                "Proven track record of delivering high-impact results."
            )
        if original and target_role:
            skill_hint = list(target_skills)[:3]
            extra = (
                f" Seeking a {target_role} role where I can leverage "
                f"{', '.join(skill_hint)} expertise."
            )
            return original.rstrip(".") + "." + extra
        return original or ""

    def _build_markdown(
        self,
        profile: UserProfile,
        bullets: list[TailoredBullet],
        reordered_skills: list[str],
        summary: str,
    ) -> str:
        lines = [
            f"# {profile.name}",
            f"**{profile.title}**",
            "",
        ]

        if summary:
            lines.append(summary)
            lines.append("")

        lines.append("## Skills")
        for skill in reordered_skills:
            lines.append(f"- {skill}")
        lines.append("")

        lines.append("## Experience")
        for exp in profile.experience:
            lines.append(f"### {exp.title} at {exp.company}")
            lines.append(f"*{exp.start_date} - {exp.end_date or 'Present'}*")
            exp_bullets = [
                b.tailored
                for b in bullets
                if any(b.original in exp.bullets for _ in [True])
            ]
            if not exp_bullets:
                exp_bullets = exp.bullets
            for b in exp_bullets:
                lines.append(f"- {b}")
            lines.append("")

        if profile.education:
            lines.append("## Education")
            for edu in profile.education:
                lines.append(f"- {edu.degree} in {edu.field}, {edu.institution} ({edu.year})")
            lines.append("")

        if profile.projects:
            lines.append("## Projects")
            for proj in profile.projects:
                lines.append(f"### {proj.name}")
                lines.append(proj.description)
                if proj.technologies:
                    lines.append(f"*Technologies: {', '.join(proj.technologies)}*")
                lines.append("")

        return "\n".join(lines).strip()
