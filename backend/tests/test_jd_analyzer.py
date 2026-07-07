from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.jd_analyzer.agent import JDAnalyzerAgent
from app.agents.jd_analyzer.models import JDAnalyzerInput, JDAnalyzerOutput, Skill
from app.agents.llm import LLMClient


SAMPLE_JD = """Senior Software Engineer - Backend

We are looking for a Senior Software Engineer to join our Platform team. You will design, build, and maintain scalable backend services.

Requirements:
- 5+ years of experience in backend development
- Strong proficiency in Python, TypeScript, and SQL
- Experience with Docker, Kubernetes, and AWS
- Deep understanding of REST APIs and microservices architecture
- Experience with PostgreSQL and Redis
- Excellent communication and leadership skills

Preferred:
- Experience with GraphQL
- Knowledge of CI/CD pipelines
- Machine Learning or NLP experience is a plus

Bachelor's degree in Computer Science or related field required.
"""


class TestJDAnalyzerAgentKeywordFallback:
    @pytest.fixture
    def agent(self) -> JDAnalyzerAgent:
        return JDAnalyzerAgent()

    @pytest.mark.asyncio
    async def test_returns_output_for_valid_input(self, agent):
        result = await agent.run(JDAnalyzerInput(raw_description=SAMPLE_JD, job_title="Senior Software Engineer"))

        assert isinstance(result, JDAnalyzerOutput)
        assert result.role_title == "Senior Software Engineer"
        assert len(result.skills) > 0
        assert len(result.tools) > 0
        assert len(result.keywords) > 0

    @pytest.mark.asyncio
    async def test_extracts_experience_requirement(self, agent):
        result = await agent.run(JDAnalyzerInput(raw_description=SAMPLE_JD))

        assert result.experience_required is not None
        assert result.experience_required.minimum_years >= 5

    @pytest.mark.asyncio
    async def test_extracts_required_skills(self, agent):
        result = await agent.run(JDAnalyzerInput(raw_description=SAMPLE_JD))

        skill_names = [s.name.lower() for s in result.skills]
        assert "python" in skill_names
        assert "typescript" in skill_names
        assert "sql" in skill_names

    @pytest.mark.asyncio
    async def test_extracts_tools(self, agent):
        result = await agent.run(JDAnalyzerInput(raw_description=SAMPLE_JD))

        tool_names = [t.lower() for t in result.tools]
        assert any("docker" in t for t in tool_names)
        assert any("kubernetes" in t for t in tool_names)

    @pytest.mark.asyncio
    async def test_extracts_soft_skills(self, agent):
        result = await agent.run(JDAnalyzerInput(raw_description=SAMPLE_JD))

        soft_names = [s.lower() for s in result.soft_skills]
        assert any("communication" in s or "leadership" in s for s in soft_names)

    @pytest.mark.asyncio
    async def test_returns_empty_output_for_empty_description(self, agent):
        result = await agent.run(JDAnalyzerInput(raw_description=""))

        assert result.role_title == ""
        assert result.skills == []

    @pytest.mark.asyncio
    async def test_extracts_qualifications(self, agent):
        result = await agent.run(JDAnalyzerInput(raw_description=SAMPLE_JD))

        assert len(result.qualifications) > 0
        has_degree = any("bachelor" in q.lower() or "computer science" in q.lower() for q in result.qualifications)
        assert has_degree

    @pytest.mark.asyncio
    async def test_generates_summary(self, agent):
        result = await agent.run(JDAnalyzerInput(
            raw_description=SAMPLE_JD,
            job_title="Senior Software Engineer",
        ))

        assert len(result.summary) > 0
        assert "Senior Software Engineer" in result.summary or "senior" in result.summary.lower()

    @pytest.mark.asyncio
    async def test_extracts_keywords(self, agent):
        result = await agent.run(JDAnalyzerInput(raw_description=SAMPLE_JD))

        assert len(result.keywords) > 0

    @pytest.mark.asyncio
    async def test_extracts_responsibilities(self, agent):
        result = await agent.run(JDAnalyzerInput(raw_description=SAMPLE_JD))

        # Responsibilities may come from bullet extraction or sentence fallback
        total_content = len(result.responsibilities) + len(result.qualifications)
        assert total_content > 0

    @pytest.mark.asyncio
    async def test_handles_minimal_input(self, agent):
        result = await agent.run(JDAnalyzerInput(raw_description="Entry level position available."))

        assert isinstance(result, JDAnalyzerOutput)


class TestJDAnalyzerAgentWithLLM:
    @pytest.fixture
    def mock_llm_client(self) -> LLMClient:
        client = MagicMock(spec=LLMClient)
        provider = MagicMock()
        client.provider = provider
        return client

    @pytest.fixture
    def agent(self, mock_llm_client) -> JDAnalyzerAgent:
        return JDAnalyzerAgent(llm_client=mock_llm_client)

    @pytest.mark.asyncio
    async def test_uses_llm_when_available(self, agent, mock_llm_client):
        mock_llm_client.generate_structured = AsyncMock(return_value={
            "skills": [
                {"name": "Python", "category": "language", "importance": "required"},
            ],
            "experience_required": {"minimum_years": 5, "maximum_years": 8, "level": "senior"},
            "tools": ["Docker", "Kubernetes"],
            "responsibilities": ["Build scalable services"],
            "qualifications": ["BS in CS"],
            "soft_skills": ["Communication"],
            "keywords": ["Python", "Docker"],
            "summary": "Senior backend role requiring Python and Docker expertise.",
            "role_title": "Senior Software Engineer",
            "industry": "Technology",
        })

        result = await agent.run(JDAnalyzerInput(
            raw_description=SAMPLE_JD,
            job_title="Senior Software Engineer",
        ))

        mock_llm_client.generate_structured.assert_called_once()
        assert result.role_title == "Senior Software Engineer"
        assert len(result.skills) == 1
        assert result.skills[0].name == "Python"

    @pytest.mark.asyncio
    async def test_falls_back_on_llm_error(self, agent, mock_llm_client):
        mock_llm_client.generate_structured = AsyncMock(side_effect=Exception("LLM unavailable"))

        result = await agent.run(JDAnalyzerInput(
            raw_description=SAMPLE_JD,
            job_title="Senior Software Engineer",
        ))

        assert result.role_title == "Senior Software Engineer"
        assert len(result.skills) > 0

    @pytest.mark.asyncio
    async def test_handles_malformed_llm_response(self, agent, mock_llm_client):
        mock_llm_client.generate_structured = AsyncMock(return_value={
            "skills": [{"not_a_field": "garbage"}],
            "tools": [],
            "responsibilities": [],
            "qualifications": [],
            "soft_skills": [],
            "keywords": [],
            "summary": "",
            "role_title": "Engineer",
        })

        result = await agent.run(JDAnalyzerInput(
            raw_description=SAMPLE_JD,
            job_title="Engineer",
        ))

        assert result.role_title == "Engineer"
        assert len(result.skills) == 0


class TestJDAnalyzerEdgeCases:
    @pytest.fixture
    def agent(self) -> JDAnalyzerAgent:
        return JDAnalyzerAgent()

    @pytest.mark.asyncio
    async def test_handles_empty_description(self, agent):
        result = await agent.run(JDAnalyzerInput(raw_description=""))
        assert isinstance(result, JDAnalyzerOutput)

    @pytest.mark.asyncio
    async def test_handles_whitespace_only_description(self, agent):
        result = await agent.run(JDAnalyzerInput(raw_description="   \n   "))
        assert isinstance(result, JDAnalyzerOutput)

    @pytest.mark.asyncio
    async def test_handles_very_short_description(self, agent):
        result = await agent.run(JDAnalyzerInput(raw_description="Hiring now!"))
        assert isinstance(result, JDAnalyzerOutput)

    @pytest.mark.asyncio
    async def test_extracts_importance_levels(self, agent):
        jd = "Python is required. Java is preferred. Rust is a plus."
        result = await agent.run(JDAnalyzerInput(raw_description=jd))
        for skill in result.skills:
            if skill.name.lower() == "python":
                assert skill.importance == "required"

    @pytest.mark.asyncio
    async def test_responsibilities_extraction(self, agent):
        jd = "Responsibilities:\n- Design APIs\n- Write tests\n- Review code"
        result = await agent.run(JDAnalyzerInput(raw_description=jd))
        assert len(result.responsibilities) > 0 or len(result.summary) > 0
