from __future__ import annotations

import json
import re
from typing import Any, Optional

from app.agents.jd_analyzer.models import (
    ExperienceRequirement,
    JDAnalyzerInput,
    JDAnalyzerOutput,
    Skill,
)
from app.agents.llm import LLMClient
from app.collectors.logging import CollectorLoggerProtocol


class JDAnalyzerAgent:
    """Analyze raw job descriptions and extract structured metadata.

    Uses LLM-based extraction with a keyword-based fallback when the
    LLM is unavailable or the provider is not configured.
    """

    SYSTEM_PROMPT = """You are a Job Description Analyzer. Extract structured information from job descriptions.

Return ONLY valid JSON with this schema:
{
  "skills": [{"name": str, "category": str, "importance": "required"|"preferred"|"bonus"}],
  "experience_required": {"minimum_years": int|null, "maximum_years": int|null, "level": str|null},
  "tools": [str],
  "responsibilities": [str],
  "qualifications": [str],
  "soft_skills": [str],
  "keywords": [str],
  "summary": str,
  "role_title": str,
  "industry": str|null
}

Categories for skills: language, framework, tool, concept, soft_skill, platform, database, cloud, library
Experience levels: entry, mid, senior, lead, principal
Be thorough. Extract every relevant skill, tool, and keyword."""

    SKILL_PATTERNS: list[tuple[str, str]] = [
        (r"(?i)\bPython\b", "language"),
        (r"(?i)\bJavaScript\b", "language"),
        (r"(?i)\bTypeScript\b", "language"),
        (r"(?i)\bJava\b", "language"),
        (r"(?i)\bGo\b", "language"),
        (r"(?i)\bRust\b", "language"),
        (r"(?i)\bC\#\b", "language"),
        (r"(?i)\bC\+\+\b", "language"),
        (r"(?i)\bRuby\b", "language"),
        (r"(?i)\bPHP\b", "language"),
        (r"(?i)\bSwift\b", "language"),
        (r"(?i)\bKotlin\b", "language"),
        (r"(?i)\bSQL\b", "language"),
        (r"(?i)\bReact\b", "framework"),
        (r"(?i)\bAngular\b", "framework"),
        (r"(?i)\bVue\.?\s*[Jj]s\b", "framework"),
        (r"(?i)\bDjango\b", "framework"),
        (r"(?i)\bFlask\b", "framework"),
        (r"(?i)\bFastAPI\b", "framework"),
        (r"(?i)\bSpring\b", "framework"),
        (r"(?i)\bNode\.?\s*[Jj]s\b", "framework"),
        (r"(?i)\bExpress\b", "framework"),
        (r"(?i)\bNext\.?\s*[Jj]s\b", "framework"),
        (r"(?i)\bDocker\b", "tool"),
        (r"(?i)\bKubernetes\b", "tool"),
        (r"(?i)\bTerraform\b", "tool"),
        (r"(?i)\bAWS\b", "platform"),
        (r"(?i)\bAzure\b", "platform"),
        (r"(?i)\bGCP\b", "platform"),
        (r"(?i)\bGit\b", "tool"),
        (r"(?i)\bLinux\b", "tool"),
        (r"(?i)\bPostgreSQL\b", "database"),
        (r"(?i)\bMySQL\b", "database"),
        (r"(?i)\bMongoDB\b", "database"),
        (r"(?i)\bRedis\b", "database"),
        (r"(?i)\bDynamoDB\b", "database"),
        (r"(?i)\bGraphQL\b", "tool"),
        (r"(?i)\bREST\b", "concept"),
        (r"(?i)\bCI/CD\b", "tool"),
        (r"(?i)\bMachine Learning\b", "concept"),
        (r"(?i)\bNLP\b", "concept"),
        (r"(?i)\bLLM\b", "concept"),
    ]

    SOFT_SKILL_PATTERNS = [
        r"(?i)\bcommunication\b",
        r"(?i)\bleadership\b",
        r"(?i)\bteamwork\b",
        r"(?i)\bproblem.solving\b",
        r"(?i)\bcritical thinking\b",
        r"(?i)\bcollaboration\b",
        r"(?i)\bmentorship\b",
        r"(?i)\bagile\b",
        r"(?i)\btime management\b",
        r"(?i)\binterpersonal\b",
    ]

    EXPERIENCE_RE = re.compile(
        r"(\d+)\s*[-to\u2013\u2014+]*\s*(\d+)?\s*(?:years?|yrs?)",
        re.IGNORECASE,
    )

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        logger: Optional[CollectorLoggerProtocol] = None,
    ) -> None:
        self._llm = llm_client
        self._logger = logger

    async def run(self, input_data: JDAnalyzerInput) -> JDAnalyzerOutput:
        if not input_data.raw_description or not input_data.raw_description.strip():
            return JDAnalyzerOutput(role_title=input_data.job_title or "")

        if self._llm is not None and self._llm.provider is not None:
            try:
                return await self._analyze_with_llm(input_data)
            except Exception as e:
                if self._logger:
                    self._logger.warning(
                        f"LLM JD analysis failed, falling back to keyword extraction: {e}"
                    )

        return self._analyze_with_keywords(input_data)

    async def _analyze_with_llm(self, input_data: JDAnalyzerInput) -> JDAnalyzerOutput:
        prompt = self._build_llm_prompt(input_data)
        result = await self._llm.generate_structured(
            prompt=prompt,
            system_prompt=self.SYSTEM_PROMPT,
        )

        return self._parse_llm_response(result, input_data)

    def _build_llm_prompt(self, input_data: JDAnalyzerInput) -> str:
        parts = ["Analyze the following job description and extract structured information."]
        if input_data.job_title:
            parts.append(f"\nJob Title: {input_data.job_title}")
        if input_data.department:
            parts.append(f"Department: {input_data.department}")
        parts.append(f"\n--- JOB DESCRIPTION ---\n{input_data.raw_description}\n--- END ---")
        return "\n".join(parts)

    def _parse_llm_response(
        self,
        result: dict[str, Any],
        input_data: JDAnalyzerInput,
    ) -> JDAnalyzerOutput:
        skills: list[Skill] = []
        for s in result.get("skills", []):
            try:
                skills.append(Skill(**s))
            except (TypeError, ValueError):
                continue

        exp_raw = result.get("experience_required", {})
        try:
            experience = ExperienceRequirement(**exp_raw) if isinstance(exp_raw, dict) else ExperienceRequirement()
        except (TypeError, ValueError):
            experience = ExperienceRequirement()

        return JDAnalyzerOutput(
            skills=skills,
            experience_required=experience,
            tools=result.get("tools", []),
            responsibilities=result.get("responsibilities", []),
            qualifications=result.get("qualifications", []),
            soft_skills=result.get("soft_skills", []),
            keywords=result.get("keywords", []),
            summary=result.get("summary", ""),
            role_title=result.get("role_title", input_data.job_title or ""),
            industry=result.get("industry"),
        )

    def _analyze_with_keywords(self, input_data: JDAnalyzerInput) -> JDAnalyzerOutput:
        text = input_data.raw_description
        title = input_data.job_title or ""

        skills = self._extract_skills(text)
        tools = self._extract_tools(text)
        soft_skills = self._extract_soft_skills(text)
        keywords = self._extract_keywords(text)
        experience = self._extract_experience(text)
        responsibilities = self._extract_bullets(text)
        qualifications = self._extract_qualifications(text)
        summary = self._generate_summary(text, title, skills, tools)

        return JDAnalyzerOutput(
            skills=skills,
            experience_required=experience,
            tools=tools,
            responsibilities=responsibilities,
            qualifications=qualifications,
            soft_skills=soft_skills,
            keywords=keywords,
            summary=summary,
            role_title=title,
            industry=None,
        )

    def _extract_skills(self, text: str) -> list[Skill]:
        found: dict[str, Skill] = {}
        for pattern, category in self.SKILL_PATTERNS:
            m = re.search(pattern, text)
            if m:
                name = m.group(0)
                lower = name.lower()
                if lower not in found:
                    importance = self._infer_importance(text, name)
                    found[lower] = Skill(name=name, category=category, importance=importance)
        return list(found.values())

    def _infer_importance(self, text: str, skill: str) -> str:
        lower = text.lower()
        if re.search(rf"(?i)(must|required|essential|need|require|pre-?req)", lower[:200]):
            return "required"
        if re.search(rf"(?i)(preferred|plus|bonus|nice to have|desired)", lower[:200]):
            return "preferred"
        return "required"

    def _extract_tools(self, text: str) -> list[str]:
        tool_patterns = [
            r"(?i)\bDocker\b",
            r"(?i)\bKubernetes\b",
            r"(?i)\bTerraform\b",
            r"(?i)\bGit\b",
            r"(?i)\bJenkins\b",
            r"(?i)\bGitHub Actions\b",
            r"(?i)\bCircleCI\b",
            r"(?i)\bJira\b",
            r"(?i)\bConfluence\b",
            r"(?i)\bGrafana\b",
            r"(?i)\bPrometheus\b",
            r"(?i)\bDatadog\b",
            r"(?i)\bELK\b",
            r"(?i)\bKafka\b",
            r"(?i)\bRabbitMQ\b",
        ]
        found = []
        for pattern in tool_patterns:
            if re.search(pattern, text):
                m = re.search(pattern, text)
                if m:
                    name = m.group(0)
                    if name not in found:
                        found.append(name)
        return found

    def _extract_soft_skills(self, text: str) -> list[str]:
        found = []
        for pattern in self.SOFT_SKILL_PATTERNS:
            m = re.search(pattern, text)
            if m:
                skill = m.group(0).strip()
                if skill not in found:
                    found.append(skill)
        return found

    def _extract_keywords(self, text: str) -> list[str]:
        words = re.findall(r"[A-Z][a-z]+(?:\s[A-Z][a-z]+)*", text)
        return list(dict.fromkeys(w for w in words if len(w) > 3))[:30]

    def _extract_experience(self, text: str) -> ExperienceRequirement:
        m = self.EXPERIENCE_RE.search(text)
        if m:
            min_years = int(m.group(1))
            max_years = int(m.group(2)) if m.group(2) else None
            level = self._years_to_level(float(max_years or min_years))
            return ExperienceRequirement(
                minimum_years=min_years,
                maximum_years=max_years,
                level=level,
            )

        level_keywords = {
            "entry": r"(?i)\b(entry.level|junior|fresher|graduate|new grad)\b",
            "mid": r"(?i)\b(mid.level|mid|intermediate|associate)\b",
            "senior": r"(?i)\b(senior|sr\.?)\b",
            "lead": r"(?i)\b(lead|staff|head)\b",
            "principal": r"(?i)\b(principal|architect|distinguished)\b",
        }
        for level, pattern in level_keywords.items():
            if re.search(pattern, text):
                return ExperienceRequirement(level=level)
        return ExperienceRequirement()

    def _years_to_level(self, years: float) -> str:
        if years <= 2:
            return "entry"
        if years <= 5:
            return "mid"
        if years <= 10:
            return "senior"
        if years <= 15:
            return "lead"
        return "principal"

    def _extract_bullets(self, text: str) -> list[str]:
        bullets = re.findall(
            r"(?:^|\n)\s*[-*\u2022\u25E6\u25AA\u25CF\d+\.]\s*(.+?)(?=\n\s*[-*\u2022\u25E6\u25AA\u25CF\d+\.]|\n\n|\Z)",
            text,
            re.DOTALL,
        )
        result = [b.strip() for b in bullets if len(b.strip()) > 15]
        if not result:
            sentences = re.split(r"[.!?]\s+", text.strip())
            result = [s.strip() for s in sentences if len(s.strip()) > 30][:10]
        return result[:15]

    def _extract_qualifications(self, text: str) -> list[str]:
        quals = []
        edu_patterns = [
            r"(?i)(?:Bachelor|Master|PhD|B\.?[AS]\.?|M\.?[AS]\.?|Ph\.?D)",
            r"(?i)(?:degree in|degree from|bachelor|master|doctorate)",
            r"(?i)(?:certification|certified|certificate)",
        ]
        for pattern in edu_patterns:
            for m in re.finditer(pattern, text):
                start = max(0, m.start() - 30)
                end = min(len(text), m.end() + 80)
                snippet = text[start:end].strip()
                if snippet not in quals:
                    quals.append(snippet)
        return quals[:8]

    def _generate_summary(
        self,
        text: str,
        title: str,
        skills: list[Skill],
        tools: list[str],
    ) -> str:
        skill_names = [s.name for s in skills[:5]]
        tool_names = tools[:3]
        parts = [f"Role: {title}."] if title else []
        if skill_names:
            parts.append(f"Requires skills in: {', '.join(skill_names)}.")
        if tool_names:
            parts.append(f"Tools: {', '.join(tool_names)}.")
        first_sentence = re.split(r"[.!?]", text.strip())[0] if text.strip() else ""
        if first_sentence and len(first_sentence) > 20:
            parts.insert(0, first_sentence + ".")
        return " ".join(parts)
