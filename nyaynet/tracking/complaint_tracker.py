"""Complaint status tracking and confirmation storage."""

from config.constants import ComplaintStatus
from config.logging_config import get_logger
from nyaynet.common.audit_logger import AuditLogger
from nyaynet.common.utils import utc_now_iso
from nyaynet.storage.repositories import ComplaintRepository

log = get_logger(__name__)


class ComplaintTracker:
    """Tracks complaint status and stores confirmations."""

    def __init__(
        self,
        complaint_repo: ComplaintRepository,
        audit_logger: AuditLogger,
    ):
        self._repo = complaint_repo
        self._audit = audit_logger

    def get_active_complaints(self) -> list[dict]:
        """Get all active (non-resolved) complaints."""
        return self._repo.get_active()

    def update_status(self, complaint_id: str, new_status: ComplaintStatus, **kwargs) -> None:
        """Update the status of a complaint."""
        self._repo.update_status(
            complaint_id,
            new_status.value,
            last_checked=utc_now_iso(),
            **kwargs,
        )

        self._audit.log(
            action="complaint_status_updated",
            entity_type="complaint",
            entity_id=complaint_id,
            details={"new_status": new_status.value},
        )

        log.info(
            "complaint_status_updated",
            complaint_id=complaint_id,
            status=new_status.value,
        )

    def get_complaint(self, complaint_id: str) -> dict | None:
        """Get a complaint by ID."""
        return self._repo.get_by_id(complaint_id)

    def get_summary(self) -> dict:
        """Get a summary of all complaints by status."""
        active = self._repo.get_active()
        summary: dict[str, int] = {}
        for complaint in active:
            status = complaint.get("status", "unknown")
            summary[status] = summary.get(status, 0) + 1
        return summary
