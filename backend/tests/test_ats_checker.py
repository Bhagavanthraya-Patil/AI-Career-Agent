from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.ats_checker.agent import ATSAnalyzerAgent
from app.agents.ats_checker.models import ATSAnalyzerInput, ATSAnalyzerOutput


SAMPLE_RESUME = """# Jane Doe
**Senior Backend Engineer**

Experienced backend engineer with 6+ years building scalable distributed systems.

## Skills
Python, TypeScript, PostgreSQL, Docker, Kubernetes, AWS, REST APIs, GraphQL

## Experience

### Senior Backend Engineer at TechCorp
*2021-01 - Present*
- Designed and built microservices architecture handling 10M+ requests/day
- Optimized PostgreSQL queries, reducing average latency by 40%
- Managed Kubernetes cluster with 50+ services

### Backend Developer at StartupInc
*2018-03 - 2020-12*
- Developed REST APIs using FastAPI and Python
- Implemented CI/CD pipelines with GitHub Actions
- Worked with Docker containerization

## Education
BS in Computer Science, State University (2018)
"""

SAMPLE_JD = """Senior Software Engineer - Backend

We are looking for a Senior Backend Engineer to join our team. You will design and build scalable distributed systems and microservices.

Requirements:
- 5+ years of backend development experience
- Strong proficiency in Python, TypeScript
- Experience with Docker, Kubernetes, AWS
- Deep understanding of REST APIs and distributed systems
- PostgreSQL expertise
- Excellent communication skills

Preferred:
- Experience with GraphQL
- CI/CD pipeline knowledge
"""


class TestATSAnalyzerKeywordFallback:
    @pytest.fixture
    def agent(self) -> ATSAnalyzerAgent:
        return ATSAnalyzerAgent()

    @pytest.mark.asyncio
    async def test_returns_output_for_valid_input(self, agent):
        result = await agent.run(ATSAnalyzerInput(
            resume_text=SAMPLE_RESUME,
            job_description=SAMPLE_JD,
        ))

        assert isinstance(result, ATSAnalyzerOutput)
        assert 0 <= result.match_score <= 100

    @pytest.mark.asyncio
    async def test_computes_match_score(self, agent):
        result = await agent.run(ATSAnalyzerInput(
            resume_text=SAMPLE_RESUME,
            job_description=SAMPLE_JD,
        ))

        assert result.match_score > 0

    @pytest.mark.asyncio
    async def test_identifies_matched_keywords(self, agent):
        result = await agent.run(ATSAnalyzerInput(
            resume_text=SAMPLE_RESUME,
            job_description=SAMPLE_JD,
        ))

        assert len(result.matched_keywords) > 0

    @pytest.mark.asyncio
    async def test_computes_keyword_density(self, agent):
        result = await agent.run(ATSAnalyzerInput(
            resume_text=SAMPLE_RESUME,
            job_description=SAMPLE_JD,
        ))

        assert 0.0 <= result.keyword_density <= 1.0

    @pytest.mark.asyncio
    async def test_provides_suggestions_when_score_low(self, agent):
        resume = "# John Doe\n**Developer**\n\nWorked on software."
        jd = "Senior Engineer requiring Python, Docker, Kubernetes, AWS, PostgreSQL, Redis, Kafka, GraphQL."
        result = await agent.run(ATSAnalyzerInput(
            resume_text=resume,
            job_description=jd,
        ))

        assert len(result.suggestions) > 0

    @pytest.mark.asyncio
    async def test_returns_zero_score_for_empty_input(self, agent):
        result = await agent.run(ATSAnalyzerInput(
            resume_text="",
            job_description=SAMPLE_JD,
        ))

        assert result.match_score == 0

    @pytest.mark.asyncio
    async def test_computes_readability_score(self, agent):
        result = await agent.run(ATSAnalyzerInput(
            resume_text=SAMPLE_RESUME,
            job_description=SAMPLE_JD,
        ))

        assert 0 <= result.readability_score <= 100

    @pytest.mark.asyncio
    async def test_generates_section_scores(self, agent):
        result = await agent.run(ATSAnalyzerInput(
            resume_text=SAMPLE_RESUME,
            job_description=SAMPLE_JD,
        ))

        assert len(result.section_scores) > 0
        for section_score in result.section_scores:
            assert 0 <= section_score.score <= 100

    @pytest.mark.asyncio
    async def test_identifies_missing_keywords(self, agent):
        result = await agent.run(ATSAnalyzerInput(
            resume_text=SAMPLE_RESUME,
            job_description=SAMPLE_JD,
        ))

        assert isinstance(result.missing_keywords, list)

    @pytest.mark.asyncio
    async def test_keyword_match_detection(self, agent):
        result = await agent.run(ATSAnalyzerInput(
            resume_text=SAMPLE_RESUME,
            job_description=SAMPLE_JD,
        ))

        assert len(result.keyword_matches) > 0

    @pytest.mark.asyncio
    async def test_ats_friendly_flag(self, agent):
        result = await agent.run(ATSAnalyzerInput(
            resume_text=SAMPLE_RESUME,
            job_description=SAMPLE_JD,
        ))

        assert isinstance(result.ats_friendly, bool)

    @pytest.mark.asyncio
    async def test_handles_identical_texts(self, agent):
        text = "Python Docker Kubernetes AWS PostgreSQL"
        result = await agent.run(ATSAnalyzerInput(
            resume_text=text,
            job_description=text,
        ))

        assert result.match_score > 50

    @pytest.mark.asyncio
    async def test_generates_suggestions(self, agent):
        result = await agent.run(ATSAnalyzerInput(
            resume_text=SAMPLE_RESUME,
            job_description=SAMPLE_JD,
        ))

        assert len(result.suggestions) > 0
        assert all(isinstance(s, str) for s in result.suggestions)

    @pytest.mark.asyncio
    async def test_per_keyword_details(self, agent):
        jd = "Strong proficiency in Python and Docker required."
        resume = "I know Python."
        result = await agent.run(ATSAnalyzerInput(
            resume_text=resume,
            job_description=jd,
        ))

        for kw in result.keyword_matches:
            if kw.keyword.lower() == "python":
                assert kw.in_resume is True
            elif kw.keyword.lower() == "docker":
                assert kw.in_resume is False

    @pytest.mark.asyncio
    async def test_low_readability_penalty(self, agent):
        bad_resume = "this is a resume with no headers no bullets no structure its just a wall of text describing work experience but no actual formatting that an ats would recognize so it should score poorly on readability"
        result = await agent.run(ATSAnalyzerInput(
            resume_text=bad_resume,
            job_description=SAMPLE_JD,
        ))

        assert result.readability_score < 80

    @pytest.mark.asyncio
    async def test_handles_resume_with_extra_keywords(self, agent):
        result = await agent.run(ATSAnalyzerInput(
            resume_text=SAMPLE_RESUME + "\n\n## Certifications\nAWS Certified Solutions Architect",
            job_description=SAMPLE_JD,
        ))

        assert result.match_score > 0
        aws_matches = [k for k in result.keyword_matches if "aws" in k.keyword.lower()]
        assert any(k.in_resume for k in aws_matches) or "aws" in " ".join(result.matched_keywords).lower()


class TestATSAnalyzerWithLLM:
    @pytest.fixture
    def mock_llm_client(self):
        client = MagicMock()
        provider = MagicMock()
        client.provider = provider
        return client

    @pytest.fixture
    def agent(self, mock_llm_client) -> ATSAnalyzerAgent:
        return ATSAnalyzerAgent(llm_client=mock_llm_client)

    @pytest.mark.asyncio
    async def test_uses_llm_when_available(self, agent, mock_llm_client):
        mock_llm_client.generate_structured = AsyncMock(return_value={
            "match_score": 75,
            "keyword_matches": [
                {"keyword": "Python", "in_resume": True, "count_in_jd": 2, "count_in_resume": 3},
            ],
            "missing_keywords": ["Kafka"],
            "matched_keywords": ["Python", "Docker", "Kubernetes"],
            "keyword_density": 0.75,
            "readability_score": 85,
            "section_scores": [
                {"section": "skills", "score": 80, "keyword_count": 5},
                {"section": "experience", "score": 70, "keyword_count": 4},
            ],
            "suggestions": ["Add more AWS keywords."],
            "ats_friendly": True,
        })

        result = await agent.run(ATSAnalyzerInput(
            resume_text=SAMPLE_RESUME,
            job_description=SAMPLE_JD,
        ))

        mock_llm_client.generate_structured.assert_called_once()
        assert result.match_score == 75
        assert not result.ats_friendly is None

    @pytest.mark.asyncio
    async def test_falls_back_on_llm_error(self, agent, mock_llm_client):
        mock_llm_client.generate_structured = AsyncMock(side_effect=Exception("LLM unavailable"))

        result = await agent.run(ATSAnalyzerInput(
            resume_text=SAMPLE_RESUME,
            job_description=SAMPLE_JD,
        ))

        assert result.match_score > 0
        assert len(result.suggestions) > 0
