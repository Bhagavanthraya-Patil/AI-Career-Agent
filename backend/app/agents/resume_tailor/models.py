from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class WorkExperience(BaseModel):
    company: str = Field(description="Company name")
    title: str = Field(description="Job title at the company")
    start_date: str = Field(description="Start date (YYYY-MM or free text)")
    end_date: Optional[str] = Field(default=None, description="End date or 'Present'")
    bullets: list[str] = Field(default_factory=list, description="Bullet points describing achievements")


class Education(BaseModel):
    institution: str = Field(description="School or university name")
    degree: str = Field(description="Degree type (BS, MS, PhD, etc.)")
    field: str = Field(description="Field of study")
    year: str = Field(description="Graduation year")


class Project(BaseModel):
    name: str = Field(description="Project name")
    description: str = Field(description="Brief description of the project")
    technologies: list[str] = Field(default_factory=list, description="Technologies used")


class UserProfile(BaseModel):
    name: str = Field(description="Candidate's full name")
    title: str = Field(description="Current or target job title")
    summary: str = Field(default="", description="Professional summary or objective")
    skills: list[str] = Field(default_factory=list, description="List of skills")
    experience: list[WorkExperience] = Field(default_factory=list, description="Work history")
    education: list[Education] = Field(default_factory=list, description="Educational background")
    projects: list[Project] = Field(default_factory=list, description="Notable projects")


class ResumeTailorInput(BaseModel):
    user_profile: UserProfile = Field(description="The candidate's full profile")
    target_skills: list[str] = Field(default_factory=list, description="Skills the JD emphasizes")
    target_keywords: list[str] = Field(default_factory=list, description="Keywords from JD analysis")
    target_role: Optional[str] = Field(default=None, description="Target job title")
    target_responsibilities: list[str] = Field(default_factory=list, description="Key responsibilities from JD")
    jd_summary: Optional[str] = Field(default=None, description="JD summary for context")


class TailoredBullet(BaseModel):
    original: str = Field(description="Original bullet point from the user's experience")
    tailored: str = Field(description="Rewritten bullet point tailored to the JD")
    matched_keywords: list[str] = Field(default_factory=list, description="Keywords matched in this bullet")


class ResumeTailorOutput(BaseModel):
    tailored_bullets: list[TailoredBullet] = Field(
        default_factory=list,
        description="Original and tailored bullet points with keyword matches",
    )
    reordered_skills: list[str] = Field(
        default_factory=list,
        description="Skills reordered by relevance to target role",
    )
    summary_statement: str = Field(
        default="",
        description="Tailored professional summary targeting the JD",
    )
    markdown_resume: str = Field(
        default="",
        description="Complete resume in markdown format, ready for PDF generation",
    )
    missing_skills: list[str] = Field(
        default_factory=list,
        description="Important JD skills not found in the user's profile",
    )
