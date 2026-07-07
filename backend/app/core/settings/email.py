from __future__ import annotations

from typing import Literal, Optional

from pydantic import Field

from . import BaseConfig


class EmailSettings(BaseConfig):
    enabled: bool = Field(
        default=False,
        description="Enable email monitoring for application status tracking",
    )
    provider: Literal["imap", "gmail_api"] = Field(
        default="imap",
        description="Email provider type",
    )
    host: str = Field(
        default="",
        description="IMAP server host",
    )
    port: int = Field(
        default=993,
        description="IMAP server port",
    )
    username: str = Field(
        default="",
        description="Email account username",
    )
    password: str = Field(
        default="",
        description="Email account password or app password",
    )
    use_tls: bool = Field(
        default=True,
        description="Use TLS for IMAP connection",
    )
    inbox_name: str = Field(
        default="INBOX",
        description="Mailbox folder to monitor",
    )
    poll_interval_minutes: int = Field(
        default=15,
        description="How often to poll for new emails (minutes)",
    )
    search_senders: str = Field(
        default="",
        description="Comma-separated sender emails to watch for status updates",
    )
    gmail_client_id: str = Field(
        default="",
        description="Gmail API client ID (OAuth 2.0)",
    )
    gmail_client_secret: str = Field(
        default="",
        description="Gmail API client secret",
    )
    gmail_refresh_token: str = Field(
        default="",
        description="Gmail API refresh token",
    )
