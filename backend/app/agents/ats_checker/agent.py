from __future__ import annotations

import re
from collections import Counter
from typing import Any, Optional

from app.agents.ats_checker.models import (
    ATSAnalyzerInput,
    ATSAnalyzerOutput,
    KeywordMatch,
    SectionScore,
)
from app.agents.llm import LLMClient
from app.collectors.logging import CollectorLoggerProtocol


class ATSAnalyzerAgent:
    """Analyze resume compatibility with a job description for ATS scoring.

    Computes keyword density, match score (0-100), readability, and
    actionable improvement suggestions. Falls back to purely statistical
    analysis when the LLM is unavailable.
    """

    SYSTEM_PROMPT = """You are an ATS (Applicant Tracking System) Resume Analyzer. Compare a resume against a job description and score their compatibility.

Consider:
1. Keyword overlap — how many JD keywords appear in the resume
2. Keyword density — how frequently keywords are used
3. Section coverage — whether all key JD requirements are addressed
4. Readability — clear section headers, bullet points, consistent formatting
5. Missing skills — important JD requirements absent from the resume

Return valid JSON with this schema:
{
  "match_score": int (0-100),
  "keyword_matches": [{"keyword": str, "in_resume": bool, "count_in_jd": int, "count_in_resume": int}],
  "missing_keywords": [str],
  "matched_keywords": [str],
  "keyword_density": float (0.0-1.0),
  "readability_score": int (0-100),
  "section_scores": [{"section": str, "score": int, "keyword_count": int}],
  "suggestions": [str],
  "ats_friendly": bool
}"""

    SECTION_HEADERS = [
        "summary", "objective", "profile",
        "skills", "technologies", "core competencies",
        "experience", "work experience", "employment", "work history",
        "education", "academic",
        "projects", "certifications",
        "publications", "awards",
    ]

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        logger: Optional[CollectorLoggerProtocol] = None,
    ) -> None:
        self._llm = llm_client
        self._logger = logger

    async def run(self, input_data: ATSAnalyzerInput) -> ATSAnalyzerOutput:
        if not input_data.resume_text or not input_data.job_description:
            return ATSAnalyzerOutput(match_score=0, suggestions=["Missing resume or job description text."])

        if self._llm is not None and self._llm.provider is not None:
            try:
                return await self._analyze_with_llm(input_data)
            except Exception as e:
                if self._logger:
                    self._logger.warning(
                        f"LLM ATS analysis failed, falling back to keyword analysis: {e}"
                    )

        return self._analyze_with_keywords(input_data)

    async def _analyze_with_llm(self, input_data: ATSAnalyzerInput) -> ATSAnalyzerOutput:
        prompt = self._build_llm_prompt(input_data)
        result = await self._llm.generate_structured(
            prompt=prompt,
            system_prompt=self.SYSTEM_PROMPT,
        )
        return self._parse_llm_response(result, input_data)

    def _build_llm_prompt(self, input_data: ATSAnalyzerInput) -> str:
        lines = [
            "Compare the following Resume and Job Description, then produce an ATS compatibility score.",
            "",
            "## Resume",
            input_data.resume_text,
            "",
            "## Job Description",
            input_data.job_description,
        ]

        if input_data.jd_skills:
            lines.extend([
                "",
                "## JD Skills (pre-extracted)",
                ", ".join(input_data.jd_skills),
            ])

        if input_data.jd_keywords:
            lines.extend([
                "",
                "## JD Keywords (pre-extracted)",
                ", ".join(input_data.jd_keywords),
            ])

        lines.append("")
        lines.append("Score the resume against the job description and provide detailed keyword matching and suggestions.")

        return "\n".join(lines)

    def _parse_llm_response(self, result: dict[str, Any], input_data: ATSAnalyzerInput) -> ATSAnalyzerOutput:
        keyword_matches_raw = result.get("keyword_matches", [])
        keyword_matches = [
            KeywordMatch(
                keyword=k.get("keyword", ""),
                in_resume=k.get("in_resume", False),
                count_in_jd=k.get("count_in_jd", 0),
                count_in_resume=k.get("count_in_resume", 0),
            )
            for k in keyword_matches_raw
        ]

        section_scores_raw = result.get("section_scores", [])
        section_scores = [
            SectionScore(
                section=s.get("section", ""),
                score=s.get("score", 0),
                keyword_count=s.get("keyword_count", 0),
            )
            for s in section_scores_raw
        ]

        return ATSAnalyzerOutput(
            match_score=result.get("match_score", 0),
            keyword_matches=keyword_matches,
            missing_keywords=result.get("missing_keywords", []),
            matched_keywords=result.get("matched_keywords", []),
            keyword_density=result.get("keyword_density", 0.0),
            readability_score=result.get("readability_score", 0),
            section_scores=section_scores,
            suggestions=result.get("suggestions", []),
            ats_friendly=result.get("ats_friendly", True),
        )

    def _analyze_with_keywords(self, input_data: ATSAnalyzerInput) -> ATSAnalyzerOutput:
        resume_lower = input_data.resume_text.lower()
        jd_lower = input_data.job_description.lower()

        jd_words = self._tokenize(jd_lower)
        resume_words = self._tokenize(resume_lower)
        jd_word_freq = Counter(jd_words)
        resume_word_freq = Counter(resume_words)

        jd_keywords = self._extract_keywords(jd_lower, jd_word_freq)
        resume_keywords = set(resume_word_freq.keys())
        all_keywords = input_data.jd_keywords or jd_keywords

        keyword_matches = []
        matched = []
        missing = []

        for kw in all_keywords:
            kw_lower = kw.lower()
            count_jd = jd_word_freq.get(kw_lower, 0) or (1 if kw_lower in jd_lower else 0)
            count_resume = resume_word_freq.get(kw_lower, 0) or (1 if kw_lower in resume_lower else 0)
            in_resume = count_resume > 0 or kw_lower in resume_lower

            keyword_matches.append(KeywordMatch(
                keyword=kw,
                in_resume=in_resume,
                count_in_jd=max(1, count_jd) if kw_lower in jd_lower else 0,
                count_in_resume=count_resume,
            ))

            if in_resume:
                matched.append(kw)
            else:
                missing.append(kw)

        total = len(all_keywords)
        matched_count = len(matched)
        density = matched_count / total if total > 0 else 0.0
        match_score = int(density * 100)

        section_scores = self._compute_section_scores(resume_lower, all_keywords, matched)
        readability = self._compute_readability(input_data.resume_text)
        suggestions = self._generate_suggestions(missing, section_scores, readability, match_score)

        return ATSAnalyzerOutput(
            match_score=match_score,
            keyword_matches=keyword_matches,
            missing_keywords=missing[:20],
            matched_keywords=matched[:30],
            keyword_density=round(density, 2),
            readability_score=readability,
            section_scores=section_scores,
            suggestions=suggestions,
            ats_friendly=readability >= 60 and match_score >= 30,
        )

    def _tokenize(self, text: str) -> list[str]:
        text = re.sub(r"[^a-z0-9\s+#.]", " ", text)
        words = text.split()
        return [
            w for w in words
            if len(w) > 1 and not w.isdigit()
        ]

    def _extract_keywords(self, jd_lower: str, word_freq: Counter) -> list[str]:
        stopwords = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
            "for", "of", "with", "by", "as", "is", "was", "are", "were",
            "be", "been", "being", "have", "has", "had", "do", "does",
            "did", "will", "would", "could", "should", "may", "might",
            "shall", "can", "need", "must", "this", "that", "these",
            "those", "i", "we", "you", "our", "your", "their", "its",
            "it", "also", "more", "most", "some", "any", "each", "every",
            "all", "both", "no", "not", "nor", "only", "very", "just",
            "about", "above", "after", "again", "then", "than", "such",
            "into", "over", "between", "through", "during", "before",
            "after", "from", "up", "down", "out", "off", "under",
        }

        candidates = sorted(
            (w for w in word_freq if w not in stopwords and len(w) > 2),
            key=word_freq.get,
            reverse=True,
        )

        bigrams = re.findall(r"(?=(\b\w+\s+\w+\b))", jd_lower)
        bigram_freq = Counter(
            bg for bg in bigrams
            if all(w not in stopwords for w in bg.split())
            and len(bg) > 5
        )
        top_bigrams = [bg for bg, _ in bigram_freq.most_common(15)]

        return top_bigrams + candidates[:25]

    def _compute_section_scores(
        self,
        resume_lower: str,
        all_keywords: list[str],
        matched_keywords: list[str],
    ) -> list[SectionScore]:
        sections = self._split_sections(resume_lower)
        scores = []
        keyword_set = set(k.lower() for k in all_keywords)
        matched_set = set(k.lower() for k in matched_keywords)

        for header, content in sections:
            if not content.strip():
                continue
            section_words = set(self._tokenize(content))
            total = len(keyword_set)
            found = sum(1 for k in keyword_set if k in content or k in section_words)
            score = int((found / total) * 100) if total > 0 else 0
            scores.append(SectionScore(
                section=header.strip(),
                score=min(100, score),
                keyword_count=found,
            ))

        return scores

    def _split_sections(self, resume_lower: str) -> list[tuple[str, str]]:
        pattern = r"(?:^|\n)(#+\s*|##?\s+)(\w[\w\s]*(?::)?)"
        matches = list(re.finditer(pattern, resume_lower, re.MULTILINE))
        sections = []

        for i, m in enumerate(matches):
            header = m.group(2).strip()
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(resume_lower)
            content = resume_lower[start:end].strip()
            sections.append((header, content))

        return sections or [("entire resume", resume_lower)]

    def _compute_readability(self, text: str) -> int:
        score = 100

        has_headers = bool(re.search(r"^#{1,3}\s+\w", text, re.MULTILINE))
        if not has_headers:
            score -= 20

        has_bullets = bool(re.search(r"(?:^|\n)\s*[-*•]\s", text))
        if not has_bullets:
            score -= 15

        sections_found = 0
        for header in self.SECTION_HEADERS:
            if re.search(rf"(?mi)^{header}", text):
                sections_found += 1
        if sections_found < 2:
            score -= 15
        elif sections_found < 3:
            score -= 5

        text_clean = re.sub(r"[#*\-•>|]", "", text)
        words = text_clean.split()
        if len(words) < 50:
            score -= 20
        elif len(words) > 2000:
            score -= 10

        avg_word_len = sum(len(w) for w in words) / len(words) if words else 0
        if avg_word_len > 7:
            score -= 10

        return max(0, min(100, score))

    def _generate_suggestions(
        self,
        missing_keywords: list[str],
        section_scores: list[SectionScore],
        readability: int,
        match_score: int,
    ) -> list[str]:
        suggestions = []

        if missing_keywords:
            top_missing = missing_keywords[:8]
            suggestions.append(
                f"Add these missing keywords to your resume: {', '.join(top_missing)}."
            )

        low_sections = [s for s in section_scores if s.score < 40]
        for sec in low_sections:
            suggestions.append(
                f"Improve your '{sec.section}' section — it matches only {sec.keyword_count} "
                f"JD keywords ({sec.score}/100)."
            )

        if readability < 60:
            if readability < 40:
                suggestions.append(
                    "Use clear section headers (## Summary, ## Skills, ## Experience, ## Education) "
                    "and bullet points for better ATS readability."
                )
            suggestions.append(
                "Ensure consistent formatting — ATS parsers prefer simple markdown over complex tables."
            )

        if match_score < 30:
            suggestions.append(
                "Tailor your resume more closely to this specific job description. "
                "Use terminology directly from the JD."
            )
        elif match_score < 60:
            suggestions.append(
                "Good start! Add more JD-specific keywords and rephrase bullet points to mirror "
                "the language used in the job description."
            )

        if not suggestions:
            suggestions.append(
                "Your resume is well-optimized for this job description. "
                "Consider quantifying achievements with metrics for even stronger impact."
            )

        return suggestions[:6]
