from __future__ import annotations

from pydantic import Field

from . import BaseConfig


class ParsingSettings(BaseConfig):
    salary_default_currency: str = Field(
        default="USD",
        description="Default currency when none is detected",
    )
    salary_default_interval: str = Field(
        default="yearly",
        description="Default salary interval when none is detected",
    )
    salary_local_formats_enabled: bool = Field(
        default=True,
        description="Enable INR (LPA, CTC), EUR, GBP formats",
    )
    salary_normalize_to_yearly: bool = Field(
        default=True,
        description="Convert monthly/hourly to yearly equivalents",
    )

    location_remote_keywords: list[str] = Field(
        default=[
            "remote", "work from home", "wfh", "fully remote",
            "100% remote", "anywhere", "worldwide", "distributed",
        ],
        description="Keywords that indicate a remote position",
    )
    location_hybrid_keywords: list[str] = Field(
        default=[
            "hybrid", "hybrid remote", "partially remote",
            "flexible location", "mix of remote",
        ],
        description="Keywords that indicate a hybrid position",
    )
    location_remote_suffixes: list[str] = Field(
        default=["(remote)", "remote", "remotely"],
        description="Suffix-based remote detection",
    )

    employment_synonyms: dict[str, str] = Field(
        default={
            "full time": "full-time",
            "fulltime": "full-time",
            "full time employee": "full-time",
            "fte": "full-time",
            "permanent": "full-time",
            "regular": "full-time",
            "part time": "part-time",
            "parttime": "part-time",
            "part time employee": "part-time",
            "pte": "part-time",
            "contractor": "contract",
            "contract to hire": "contract",
            "c2h": "contract",
            "fixed term": "contract",
            "temp": "temporary",
            "temp to perm": "temporary",
            "co op": "internship",
            "co-op": "internship",
            "coop": "internship",
            "freelancer": "freelance",
            "voluntary": "volunteer",
        },
        description="Employment type synonym normalization map",
    )

    experience_year_ranges: dict[str, list[int]] = Field(
        default={
            "entry": [0, 1],
            "mid": [2, 4],
            "senior": [5, 9],
            "lead": [10, 14],
            "principal": [15, 99],
        },
        description="Year ranges for each experience level",
    )
    experience_level_keywords: dict[str, list[str]] = Field(
        default={
            "entry": ["entry", "junior", "fresher", "graduate", "new grad", "0 years"],
            "mid": ["mid", "intermediate", "associate", "3 years", "5 years"],
            "senior": ["senior", "sr", "staff", "6 years", "8 years"],
            "lead": ["lead", "head", "manager", "director", "10 years"],
            "principal": ["principal", "architect", "distinguished", "fellow", "15 years"],
        },
        description="Keywords that map to each experience level",
    )

    title_seniority_prefixes: list[str] = Field(
        default=[
            "senior", "sr", "lead", "principal", "staff", "chief",
            "head of", "director of", "vp of", "vice president",
            "junior", "jr", "associate", "assistant",
        ],
        description="Prefix-based seniority detection for title normalization",
    )
    title_stopwords: list[str] = Field(
        default=[
            "ii", "iii", "iv",
            " - ", " / ",
        ],
        description="Title tokens to strip during normalization",
    )

    metadata_date_formats: list[str] = Field(
        default=[
            "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ",
            "%m/%d/%Y", "%d/%m/%Y", "%B %d, %Y", "%b %d, %Y",
            "%Y/%m/%d", "%d-%m-%Y", "%m-%d-%Y",
        ],
        description="Date format strings for metadata date parsing",
    )
    metadata_default_categories: list[str] = Field(
        default=["engineering", "product", "design", "marketing", "sales", "data"],
        description="Default category list for classification",
    )
