from __future__ import annotations

import asyncio
from typing import Any, Optional

from app.agents.apply_agent.exceptions import SubmissionError, VerificationError
from app.collectors.logging import CollectorLoggerProtocol


class SubmitHandler:
    """Handles the final submission step of a job application.

    Supports three modes:
    - ``review``: Present pre-filled form for user review (no submission).
    - ``dry_run``: Fill the form fully but do not submit.
    - ``submit``: Perform actual submission and verify confirmation.

    Usage::

        handler = SubmitHandler(logger=logger)
        result = await handler.execute(page, context)
    """

    CONFIRMATION_PATTERNS: list[str] = [
        "thank you",
        "application submitted",
        "application received",
        "we have received",
        "your application has been",
        "submission successful",
        "successfully submitted",
        "confirmation",
        "reference number",
        "application confirmation",
    ]

    ERROR_PATTERNS: list[str] = [
        "please correct",
        "missing required",
        "errors on the page",
        "please fix",
        "required field",
        "invalid",
        "there was a problem",
    ]

    def __init__(
        self,
        screenshot_dir: Optional[str] = None,
        logger: Optional[CollectorLoggerProtocol] = None,
    ) -> None:
        self._screenshot_dir = screenshot_dir
        self._logger = logger

    def _log(self, message: str, level: str = "info") -> None:
        if self._logger:
            getattr(self._logger, level, print)(message)

    async def execute(
        self,
        page: Any,
        mode: str = "review",
    ) -> dict[str, Any]:
        """Execute the submission step based on the given mode.

        Args:
            page: A Playwright Page object with the filled form.
            mode: One of ``review``, ``dry_run``, or ``submit``.

        Returns:
            A dict with keys:
            - ``submitted``: bool
            - ``screenshot``: optional str path
            - ``confirmation_code``: optional str
            - ``errors``: list of str
            - ``page_text``: str (for verification)
        """
        result: dict[str, Any] = {
            "submitted": False,
            "screenshot": None,
            "confirmation_code": None,
            "errors": [],
            "page_text": "",
        }

        if mode == "review":
            self._log("Review mode: taking screenshot for user review")
            screenshot = await self._capture_screenshot(page, "review")
            result["screenshot"] = screenshot
            return result

        if mode == "dry_run":
            self._log("Dry-run mode: form filled but not submitted")
            screenshot = await self._capture_screenshot(page, "dry_run")
            result["screenshot"] = screenshot
            return result

        if mode == "submit":
            return await self._do_submit(page)

        raise SubmissionError(
            message=f"Unknown submission mode: {mode}",
            step="submit",
        )

    async def _do_submit(self, page: Any) -> dict[str, Any]:
        """Perform actual form submission."""
        result: dict[str, Any] = {
            "submitted": False,
            "screenshot": None,
            "confirmation_code": None,
            "errors": [],
            "page_text": "",
        }

        try:
            submit_button = await self._find_submit_button(page)
            if not submit_button:
                raise SubmissionError(
                    message="No submit button found on the page",
                    step="submit",
                )

            screenshot_before = await self._capture_screenshot(page, "pre_submit")
            result["screenshot"] = screenshot_before

            self._log("Clicking submit button")
            await submit_button.click()

            await asyncio.sleep(2)

            await page.wait_for_load_state("networkidle", timeout=15000)

            page_text = await page.inner_text("body") or ""
            result["page_text"] = page_text

            if await self._detect_error(page, page_text):
                error_screenshot = await self._capture_screenshot(page, "submit_error")
                result["screenshot"] = error_screenshot
                result["errors"].append("Error detected after submission")
                raise SubmissionError(
                    message="Error detected after form submission",
                    step="submit",
                )

            confirmation_code = await self._verify_submission(page, page_text)
            if confirmation_code:
                result["submitted"] = True
                result["confirmation_code"] = confirmation_code
                confirm_screenshot = await self._capture_screenshot(page, "confirmation")
                result["screenshot"] = confirm_screenshot
            else:
                result["submitted"] = True
                confirm_screenshot = await self._capture_screenshot(page, "post_submit")
                result["screenshot"] = confirm_screenshot

            return result

        except SubmissionError:
            raise
        except Exception as exc:
            raise SubmissionError(
                message=f"Submission failed: {exc}",
                step="submit",
                original=exc,
            ) from exc

    async def _find_submit_button(self, page: Any) -> Any:
        """Find the submit button using multiple strategies."""
        strategies = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Submit")',
            'button:has-text("Apply")',
            'button:has-text("Send")',
            'button:has-text("Continue")',
            'button:has-text("Next")',
            '[role="button"]:has-text("Submit")',
            '[role="button"]:has-text("Apply")',
            'a:has-text("Submit")',
            'a:has-text("Apply")',
        ]

        for strategy in strategies:
            try:
                button = page.locator(strategy).first
                if await button.is_visible(timeout=2000):
                    return button
            except Exception:
                continue

        return None

    async def _verify_submission(self, page: Any, page_text: str) -> Optional[str]:
        """Verify submission was successful and extract confirmation code."""
        if not page_text:
            page_text = await page.inner_text("body") or ""

        page_lower = page_text.lower()

        is_confirmed = any(p in page_lower for p in self.CONFIRMATION_PATTERNS)
        if not is_confirmed:
            return None

        confirmation_code = await self._extract_confirmation_code(page, page_text)
        return confirmation_code

    async def _extract_confirmation_code(self, page: Any, page_text: str) -> Optional[str]:
        """Extract a confirmation/reference number from the page."""
        import re

        patterns = [
            r"(?:confirmation|reference|application|submission)\s*(?:#|number|code|id|no)[:\s]*([A-Z0-9-]{4,})",
            r"(?:confirmation|reference)\s*(?:#|number|code)[:\s]*([A-Z0-9-]+)",
            r"thank\s*you[^.]*?([A-Z0-9-]{4,})",
        ]

        for pattern in patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    async def _detect_error(self, page: Any, page_text: str) -> bool:
        """Check if the page shows error messages after submission."""
        if not page_text:
            page_text = await page.inner_text("body") or ""

        page_lower = page_text.lower()
        return any(p in page_lower for p in self.ERROR_PATTERNS)

    async def _capture_screenshot(self, page: Any, label: str) -> Optional[str]:
        """Capture a screenshot of the current page."""
        try:
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"apply_{label}_{timestamp}.png"
            if self._screenshot_dir:
                import os
                screenshot_path = os.path.join(self._screenshot_dir, screenshot_path)
            await page.screenshot(path=screenshot_path, full_page=True)
            return screenshot_path
        except Exception as exc:
            self._log(f"Screenshot failed: {exc}", "warning")
            return None
