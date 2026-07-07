from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class Skill(BaseModel):
    name: str = Field(description="Name of the skill")
    category: str = Field(
        description="Category: language, framework, tool, concept, soft_skill, platform"
    )
    importance: Literal["required", "preferred", "bonus"] = Field(
        description="How important the skill is for the role"
    )


class ExperienceRequirement(BaseModel):
    minimum_years: Optional[int] = Field(default=None, description="Minimum years of experience required")
    maximum_years: Optional[int] = Field(default=None, description="Maximum years of experience")
    level: Optional[str] = Field(default=None, description="Seniority level: entry, mid, senior, lead, principal")


class JDAnalyzerInput(BaseModel):
    raw_description: str = Field(description="Raw job description text to analyze")
    job_title: Optional[str] = Field(default=None, description="Job title if available")
    department: Optional[str] = Field(default=None, description="Department name if available")


class JDAnalyzerOutput(BaseModel):
    skills: list[Skill] = Field(default_factory=list, description="Extracted skills with category and importance")
    experience_required: ExperienceRequirement = Field(
        default_factory=ExperienceRequirement,
        description="Experience requirements parsed from the JD",
    )
    tools: list[str] = Field(default_factory=list, description="Tools, platforms, and technologies mentioned")
    responsibilities: list[str] = Field(default_factory=list, description="Key responsibilities extracted from the JD")
    qualifications: list[str] = Field(default_factory=list, description="Educational and certification requirements")
    soft_skills: list[str] = Field(default_factory=list, description="Soft skills and personal attributes mentioned")
    keywords: list[str] = Field(default_factory=list, description="Important keywords and phrases for ATS matching")
    summary: str = Field(default="", description="One-paragraph summary of the role")
    role_title: str = Field(default="", description="Normalized role title")
    industry: Optional[str] = Field(default=None, description="Target industry if identifiable")
