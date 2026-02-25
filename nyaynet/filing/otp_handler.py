"""OTP handling: CLI prompt and optional email polling."""

import click

from config.logging_config import get_logger
from nyaynet.common.exceptions import OTPError

log = get_logger(__name__)


class OTPHandler:
    """Handles OTP verification during portal filing."""

    def __init__(self, method: str = "cli"):
        """Initialize OTP handler.

        Args:
            method: 'cli' for interactive prompt, 'email' for email polling
        """
        self._method = method

    def get_otp(self, prompt_message: str = "Enter OTP received") -> str:
        """Get OTP from the user.

        Returns the OTP string.
        """
        if self._method == "cli":
            return self._get_otp_cli(prompt_message)
        elif self._method == "email":
            return self._get_otp_email()
        else:
            raise OTPError(f"Unknown OTP method: {self._method}")

    def _get_otp_cli(self, prompt_message: str) -> str:
        """Prompt user for OTP via CLI."""
        click.echo("\n" + "=" * 40)
        click.echo("OTP VERIFICATION REQUIRED")
        click.echo("=" * 40)
        otp = click.prompt(prompt_message, type=str)
        if not otp or len(otp) < 4:
            raise OTPError("Invalid OTP entered")
        log.info("otp_received_via_cli")
        return otp.strip()

    def _get_otp_email(self) -> str:
        """Poll email for OTP (stub for future implementation)."""
        log.warning("email_otp_polling_not_implemented")
        # Fall back to CLI
        return self._get_otp_cli("Email OTP polling not available. Enter OTP manually")
