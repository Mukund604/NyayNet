"""Playwright-based screenshot capture for evidence."""

from datetime import datetime, timezone
from pathlib import Path

from config.logging_config import get_logger
from nyaynet.common.exceptions import ScreenshotError
from nyaynet.storage.file_store import FileStore

log = get_logger(__name__)


class ScreenshotCapture:
    """Captures screenshots of Instagram posts/profiles using Playwright."""

    def __init__(self, file_store: FileStore):
        self._file_store = file_store

    async def capture_url(self, url: str, username: str, label: str = "evidence") -> str:
        """Capture a screenshot of a URL and save it.

        Returns the file path of the saved screenshot.
        """
        try:
            from playwright.async_api import async_playwright

            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"{label}_{timestamp}.png"

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page(
                    viewport={"width": 1280, "height": 720},
                )
                await page.goto(url, wait_until="networkidle", timeout=30000)
                screenshot_bytes = await page.screenshot(full_page=True)
                await browser.close()

            file_path = self._file_store.save_screenshot(
                username, filename, screenshot_bytes
            )
            log.info("screenshot_captured", url=url, path=file_path)
            return file_path

        except ImportError:
            raise ScreenshotError("Playwright is not installed")
        except Exception as e:
            raise ScreenshotError(f"Screenshot capture failed for {url}: {e}") from e

    async def capture_post(self, post_id: str, username: str) -> str:
        """Capture a screenshot of an Instagram post."""
        url = f"https://www.instagram.com/p/{post_id}/"
        return await self.capture_url(url, username, label=f"post_{post_id}")

    async def capture_profile(self, target_username: str, evidence_username: str) -> str:
        """Capture a screenshot of an Instagram profile."""
        url = f"https://www.instagram.com/{target_username}/"
        return await self.capture_url(
            url, evidence_username, label=f"profile_{target_username}"
        )
