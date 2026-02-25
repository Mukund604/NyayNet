"""Email and webhook notifications for complaint events."""

import smtplib
from email.mime.text import MIMEText

from config.logging_config import get_logger
from config.settings import Settings

log = get_logger(__name__)


class Notifier:
    """Sends notifications about complaint status changes."""

    def __init__(self, settings: Settings):
        self._settings = settings

    def notify_complaint_filed(self, complaint_id: str, username: str) -> None:
        """Send notification when a complaint is filed."""
        subject = f"NyayNet: Complaint Filed Against @{username}"
        body = (
            f"A complaint has been successfully filed on the National Cyber Crime Portal.\n\n"
            f"Complaint ID: {complaint_id}\n"
            f"Target User: @{username}\n\n"
            f"You can track the status using: python main.py status {complaint_id}"
        )
        self._send_email(subject, body)

    def notify_decision_pending(self, decision_id: str, username: str, action: str) -> None:
        """Send notification when a decision requires human review."""
        subject = f"NyayNet: Decision Pending Review - @{username}"
        body = (
            f"A decision requires your review.\n\n"
            f"Decision ID: {decision_id}\n"
            f"Target User: @{username}\n"
            f"Recommended Action: {action}\n\n"
            f"Review using: python main.py review"
        )
        self._send_email(subject, body)

    def notify_status_change(self, complaint_id: str, old_status: str, new_status: str) -> None:
        """Send notification when a complaint status changes."""
        subject = f"NyayNet: Complaint Status Update - {complaint_id}"
        body = (
            f"Complaint status has been updated.\n\n"
            f"Complaint ID: {complaint_id}\n"
            f"Previous Status: {old_status}\n"
            f"New Status: {new_status}"
        )
        self._send_email(subject, body)

    def _send_email(self, subject: str, body: str) -> None:
        """Send an email notification."""
        if not self._settings.smtp_host or not self._settings.notification_email:
            log.debug("email_notification_skipped", reason="SMTP not configured")
            return

        try:
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = self._settings.smtp_user
            msg["To"] = self._settings.notification_email

            with smtplib.SMTP(self._settings.smtp_host, self._settings.smtp_port) as server:
                server.starttls()
                server.login(self._settings.smtp_user, self._settings.smtp_password)
                server.send_message(msg)

            log.info("email_notification_sent", subject=subject)
        except Exception as e:
            log.warning("email_notification_failed", error=str(e))
