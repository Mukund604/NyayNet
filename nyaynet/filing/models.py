"""Pydantic models for the filing module."""

from pydantic import BaseModel, Field

from config.constants import ComplaintStatus
from nyaynet.common.utils import generate_id, utc_now_iso


class ComplaintSubmission(BaseModel):
    """Data needed to submit a complaint on the portal."""

    complainant_name: str
    complainant_email: str
    complainant_phone: str
    complainant_state: str
    complainant_city: str
    category: str
    subcategory: str
    description: str
    incident_date: str
    evidence_files: list[str] = Field(default_factory=list)


class FilingResult(BaseModel):
    """Result of a complaint filing attempt."""

    id: str = Field(default_factory=generate_id)
    evidence_package_id: str
    portal_complaint_id: str | None = None
    status: ComplaintStatus = ComplaintStatus.PENDING_REVIEW
    submission_data: dict = Field(default_factory=dict)
    portal_response: str | None = None
    confirmation_screenshot: str | None = None
    filed_at: str | None = None
    updated_at: str = Field(default_factory=utc_now_iso)

    def to_db_dict(self) -> dict:
        return {
            "id": self.id,
            "evidence_package_id": self.evidence_package_id,
            "portal_complaint_id": self.portal_complaint_id,
            "status": self.status.value,
            "submission_data": self.submission_data,
            "portal_response": self.portal_response,
            "confirmation_screenshot": self.confirmation_screenshot,
            "filed_at": self.filed_at,
        }
