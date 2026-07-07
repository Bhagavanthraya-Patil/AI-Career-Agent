from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from app.agents.apply_agent.application_context import UploadedDocument
from app.agents.apply_agent.exceptions import UploadError
from app.collectors.logging import CollectorLoggerProtocol


class ResumeUploader:
    """Handles resume and document uploads on application forms.

    Uses Playwright's file chooser API to upload documents.
    Supports PDF and DOCX formats. Integrates with the storage
    layer when files need to be retrieved from configured paths.

    Usage::

        uploader = ResumeUploader(logger=logger)
        result = await uploader.upload(page, resume_path)
    """

    SUPPORTED_FORMATS: list[str] = [".pdf", ".docx", ".doc", ".txt", ".rtf"]

    def __init__(
        self,
        storage_path: Optional[str] = None,
        logger: Optional[CollectorLoggerProtocol] = None,
    ) -> None:
        self._storage_path = storage_path
        self._logger = logger

    def _log(self, message: str, level: str = "info") -> None:
        if self._logger:
            getattr(self._logger, level, print)(message)

    async def upload(self, page: Any, file_path: str) -> UploadedDocument:
        """Upload a file to the first available file input on the page.

        Args:
            page: A Playwright Page object.
            file_path: Absolute or storage-relative path to the file.

        Returns:
            An UploadedDocument with the result.

        Raises:
            UploadError: If no file input is found or upload fails.
        """
        resolved_path = self._resolve_path(file_path)
        self._validate_path(resolved_path)

        file_input = await page.query_selector('input[type="file"]')
        if not file_input:
            raise UploadError(
                message="No file input found on the page",
                step="resume_upload",
            )

        try:
            async with page.expect_file_chooser() as fc_info:
                await file_input.click()
            file_chooser = await fc_info.value
            await file_chooser.set_files(resolved_path)

            ext = Path(resolved_path).suffix.lower()
            result = UploadedDocument(
                field_selector='input[type="file"]',
                file_path=resolved_path,
                file_type=ext,
                uploaded=True,
            )
            self._log(f"Uploaded {resolved_path}")
            return result

        except Exception as exc:
            raise UploadError(
                message=f"Failed to upload {resolved_path}: {exc}",
                step="resume_upload",
                original=exc,
            ) from exc

    async def upload_to_specific_field(
        self,
        page: Any,
        file_path: str,
        field_selector: str,
    ) -> UploadedDocument:
        """Upload a file to a specific file input field.

        Args:
            page: A Playwright Page object.
            file_path: Path to the file.
            field_selector: CSS selector for the specific file input.

        Returns:
            An UploadedDocument with the result.
        """
        resolved_path = self._resolve_path(file_path)
        self._validate_path(resolved_path)

        file_input = page.locator(field_selector)
        count = await file_input.count()
        if count == 0:
            raise UploadError(
                message=f"No file input found for selector '{field_selector}'",
                step="resume_upload",
            )

        try:
            async with page.expect_file_chooser() as fc_info:
                await file_input.first.click()
            file_chooser = await fc_info.value
            await file_chooser.set_files(resolved_path)

            ext = Path(resolved_path).suffix.lower()
            result = UploadedDocument(
                field_selector=field_selector,
                file_path=resolved_path,
                file_type=ext,
                uploaded=True,
            )
            self._log(f"Uploaded {resolved_path} to {field_selector}")
            return result

        except Exception as exc:
            raise UploadError(
                message=f"Failed to upload {resolved_path} to {field_selector}: {exc}",
                step="resume_upload",
                original=exc,
            ) from exc

    def _resolve_path(self, file_path: str) -> str:
        """Resolve a file path, checking storage path as fallback."""
        if os.path.isabs(file_path):
            return file_path
        if self._storage_path:
            candidate = os.path.join(self._storage_path, file_path)
            if os.path.exists(candidate):
                return candidate
        return file_path

    def _validate_path(self, file_path: str) -> None:
        """Validate that the file exists and format is supported."""
        if not os.path.exists(file_path):
            raise UploadError(
                message=f"File not found: {file_path}",
                step="resume_upload",
            )
        ext = Path(file_path).suffix.lower()
        if ext not in self.SUPPORTED_FORMATS:
            raise UploadError(
                message=f"Unsupported file format '{ext}'. Supported: {', '.join(self.SUPPORTED_FORMATS)}",
                step="resume_upload",
            )
