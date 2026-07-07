from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .settings.app import AppSettings
from .settings.application import ApplicationSettings
from .settings.database import DatabaseSettings
from .settings.email import EmailSettings
from .settings.gemini import GeminiSettings
from .settings.job_collection import JobCollectionSettings
from .settings.logging_settings import LoggingSettings
from .settings.parsing import ParsingSettings
from .settings.playwright import PlaywrightSettings
from .settings.storage import StorageSettings


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="_",
        validate_default=True,
        extra="ignore",
    )

    app: AppSettings = Field(default_factory=AppSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    gemini: GeminiSettings = Field(default_factory=GeminiSettings)
    parsing: ParsingSettings = Field(default_factory=ParsingSettings)
    playwright: PlaywrightSettings = Field(default_factory=PlaywrightSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    email: EmailSettings = Field(default_factory=EmailSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    job_collection: JobCollectionSettings = Field(
        default_factory=JobCollectionSettings,
    )
    application: ApplicationSettings = Field(
        default_factory=ApplicationSettings,
    )


settings = Settings()
