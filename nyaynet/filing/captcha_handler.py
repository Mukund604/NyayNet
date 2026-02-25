"""CAPTCHA detection and user fallback."""

import click

from config.logging_config import get_logger
from nyaynet.common.exceptions import CaptchaError

log = get_logger(__name__)


class CaptchaHandler:
    """Handles CAPTCHA challenges during portal filing."""

    async def detect_and_solve(self, page) -> str:
        """Detect CAPTCHA on the page and prompt user for solution.

        Args:
            page: Playwright page object

        Returns:
            The CAPTCHA solution string.
        """
        from config.constants import PORTAL_SELECTORS

        try:
            # Check if CAPTCHA image is present
            captcha_img = page.locator(PORTAL_SELECTORS["captcha_image"])
            if not await captcha_img.is_visible(timeout=3000):
                log.info("no_captcha_detected")
                return ""

            # Screenshot the CAPTCHA for the user
            captcha_screenshot = await captcha_img.screenshot()

            # Save temporarily for display
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                f.write(captcha_screenshot)
                captcha_path = f.name

            click.echo("\n" + "=" * 40)
            click.echo("CAPTCHA VERIFICATION REQUIRED")
            click.echo(f"CAPTCHA image saved to: {captcha_path}")
            click.echo("Please view the image and enter the text.")
            click.echo("=" * 40)

            solution = click.prompt("Enter CAPTCHA text", type=str)
            if not solution:
                raise CaptchaError("No CAPTCHA solution provided")

            log.info("captcha_solved_by_user")
            return solution.strip()

        except CaptchaError:
            raise
        except Exception as e:
            raise CaptchaError(f"CAPTCHA handling failed: {e}") from e
