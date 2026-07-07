from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.resume_tailor.agent import ResumeTailorAgent
from app.agents.resume_tailor.models import (
    Education,
    Project,
    ResumeTailorInput,
    ResumeTailorOutput,
    UserProfile,
    WorkExperience,
)


SAMPLE_PROFILE = UserProfile(
    name="Jane Doe",
    title="Software Engineer",
    summary="Experienced backend engineer with Python expertise.",
    skills=["Python", "Flask", "PostgreSQL", "Docker", "Git"],
    experience=[
        WorkExperience(
            company="TechCorp",
            title="Backend Developer",
            start_date="2020-01",
            end_date="Present",
            bullets=[
                "Built REST APIs using Flask",
                "Managed PostgreSQL database schemas",
                "Deployed services with Docker",
            ],
        ),
        WorkExperience(
            company="StartupInc",
            title="Junior Developer",
            start_date="2018-03",
            end_date="2019-12",
            bullets=[
                "Wrote unit tests",
                "Fixed bugs in production code",
            ],
        ),
    ],
    education=[
        Education(
            institution="State University",
            degree="BS",
            field="Computer Science",
            year="2018",
        ),
    ],
    projects=[
        Project(
            name="Open Source CLI Tool",
            description="A command-line tool for automating deployments",
            technologies=["Python", "Click", "Docker"],
        ),
    ],
)


SAMPLE_TARGET_SKILLS = ["Python", "Docker", "Kubernetes", "AWS", "PostgreSQL", "FastAPI"]
SAMPLE_TARGET_KEYWORDS = ["microservices", "distributed systems", "REST", "API design", "CI/CD"]


class TestResumeTailorAgentKeywordFallback:
    @pytest.fixture
    def agent(self) -> ResumeTailorAgent:
        return ResumeTailorAgent()

    @pytest.mark.asyncio
    async def test_returns_output_for_valid_input(self, agent):
        result = await agent.run(ResumeTailorInput(
            user_profile=SAMPLE_PROFILE,
            target_skills=SAMPLE_TARGET_SKILLS,
            target_keywords=SAMPLE_TARGET_KEYWORDS,
            target_role="Senior Backend Engineer",
        ))

        assert isinstance(result, ResumeTailorOutput)
        assert len(result.tailored_bullets) > 0

    @pytest.mark.asyncio
    async def test_reorders_skills_by_relevance(self, agent):
        result = await agent.run(ResumeTailorInput(
            user_profile=SAMPLE_PROFILE,
            target_skills=["Kubernetes", "AWS", "Python", "PostgreSQL"],
            target_keywords=[],
        ))

        relevant_skills = ["Python", "PostgreSQL"]
        for skill in relevant_skills:
            assert skill in result.reordered_skills

    @pytest.mark.asyncio
    async def test_identifies_missing_skills(self, agent):
        result = await agent.run(ResumeTailorInput(
            user_profile=SAMPLE_PROFILE,
            target_skills=["Kubernetes", "AWS", "FastAPI"],
            target_keywords=[],
        ))

        assert "Kubernetes" in result.missing_skills
        assert "AWS" in result.missing_skills

    @pytest.mark.asyncio
    async def test_generates_markdown_resume(self, agent):
        result = await agent.run(ResumeTailorInput(
            user_profile=SAMPLE_PROFILE,
            target_skills=SAMPLE_TARGET_SKILLS,
            target_keywords=SAMPLE_TARGET_KEYWORDS,
            target_role="Senior Backend Engineer",
        ))

        assert "# Jane Doe" in result.markdown_resume
        assert "## Skills" in result.markdown_resume
        assert "## Experience" in result.markdown_resume
        assert "TechCorp" in result.markdown_resume

    @pytest.mark.asyncio
    async def test_returns_empty_for_empty_profile(self, agent):
        empty = UserProfile(name="", title="")
        result = await agent.run(ResumeTailorInput(
            user_profile=empty,
            target_skills=[],
            target_keywords=[],
        ))

        assert isinstance(result, ResumeTailorOutput)

    @pytest.mark.asyncio
    async def test_tailored_bullets_match_keywords(self, agent):
        result = await agent.run(ResumeTailorInput(
            user_profile=SAMPLE_PROFILE,
            target_skills=["Python", "Docker"],
            target_keywords=["REST", "API"],
            target_role="Backend Engineer",
        ))

        for bullet in result.tailored_bullets:
            assert isinstance(bullet.original, str)
            assert isinstance(bullet.tailored, str)

    @pytest.mark.asyncio
    async def test_tailors_summary_when_no_original(self, agent):
        profile = UserProfile(name="John", title="Engineer", skills=["Python"])
        result = await agent.run(ResumeTailorInput(
            user_profile=profile,
            target_skills=["Python", "Go"],
            target_role="Senior Engineer",
        ))

        assert "Senior Engineer" in result.summary_statement or len(result.summary_statement) > 0

    @pytest.mark.asyncio
    async def test_includes_education_in_markdown(self, agent):
        result = await agent.run(ResumeTailorInput(
            user_profile=SAMPLE_PROFILE,
            target_skills=SAMPLE_TARGET_SKILLS,
            target_keywords=[],
        ))

        assert "State University" in result.markdown_resume
        assert "Computer Science" in result.markdown_resume


class TestResumeTailorAgentWithLLM:
    @pytest.fixture
    def mock_llm_client(self):
        client = MagicMock()
        provider = MagicMock()
        client.provider = provider
        return client

    @pytest.fixture
    def agent(self, mock_llm_client) -> ResumeTailorAgent:
        return ResumeTailorAgent(llm_client=mock_llm_client)

    @pytest.mark.asyncio
    async def test_uses_llm_when_available(self, agent, mock_llm_client):
        mock_llm_client.generate_structured = AsyncMock(return_value={
            "tailored_bullets": [
                {
                    "original": "Built REST APIs using Flask",
                    "tailored": "Designed and built scalable REST APIs using Flask and Python",
                    "matched_keywords": ["REST", "API"],
                },
            ],
            "reordered_skills": ["Python", "Flask", "Docker", "PostgreSQL", "Git"],
            "summary_statement": "Experienced backend engineer with expertise in Python and Flask.",
            "missing_skills": ["Kubernetes", "AWS"],
        })

        result = await agent.run(ResumeTailorInput(
            user_profile=SAMPLE_PROFILE,
            target_skills=SAMPLE_TARGET_SKILLS,
            target_keywords=SAMPLE_TARGET_KEYWORDS,
            target_role="Senior Backend Engineer",
        ))

        mock_llm_client.generate_structured.assert_called_once()
        assert len(result.tailored_bullets) == 1
        assert result.tailored_bullets[0].original == "Built REST APIs using Flask"

    @pytest.mark.asyncio
    async def test_falls_back_on_llm_error(self, agent, mock_llm_client):
        mock_llm_client.generate_structured = AsyncMock(side_effect=Exception("LLM unavailable"))

        result = await agent.run(ResumeTailorInput(
            user_profile=SAMPLE_PROFILE,
            target_skills=SAMPLE_TARGET_SKILLS,
            target_keywords=SAMPLE_TARGET_KEYWORDS,
        ))

        assert len(result.tailored_bullets) > 0
