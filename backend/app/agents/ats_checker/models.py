from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ATSAnalyzerInput(BaseModel):
    resume_text: str = Field(description="Resume text (markdown or plain text) to analyze")
    job_description: str = Field(description="Job description text to compare against")
    jd_skills: Optional[list[str]] = Field(default=None, description="Pre-extracted JD skills for keyword matching")
    jd_keywords: Optional[list[str]] = Field(default=None, description="Pre-extracted JD keywords")


class KeywordMatch(BaseModel):
    keyword: str = Field(description="The keyword being matched")
    in_resume: bool = Field(description="Whether the keyword appears in the resume")
    count_in_jd: int = Field(description="Number of times the keyword appears in the JD")
    count_in_resume: int = Field(description="Number of times the keyword appears in the resume")


class SectionScore(BaseModel):
    section: str = Field(description="Resume section name (summary, skills, experience, education)")
    score: int = Field(description="Score for this section out of 100")
    keyword_count: int = Field(description="Number of JD keywords found in this section")


class ATSAnalyzerOutput(BaseModel):
    match_score: int = Field(description="Overall match score (0-100)")
    keyword_matches: list[KeywordMatch] = Field(
        default_factory=list,
        description="Per-keyword match results",
    )
    missing_keywords: list[str] = Field(
        default_factory=list,
        description="Important JD keywords missing from the resume",
    )
    matched_keywords: list[str] = Field(
        default_factory=list,
        description="JD keywords that appear in the resume",
    )
    keyword_density: float = Field(
        default=0.0,
        description="Ratio of matched keywords to total JD keywords",
    )
    readability_score: int = Field(
        default=0,
        description="Readability score (0-100) based on structure and formatting",
    )
    section_scores: list[SectionScore] = Field(
        default_factory=list,
        description="Per-section keyword match scores",
    )
    suggestions: list[str] = Field(
        default_factory=list,
        description="Actionable improvement suggestions",
    )
    ats_friendly: bool = Field(
        default=True,
        description="Whether the resume appears to be ATS-friendly",
    )
