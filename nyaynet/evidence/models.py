"""Pydantic models for the evidence module."""

from pydantic import BaseModel, Field

from nyaynet.common.utils import generate_id, utc_now_iso


class EvidencePackage(BaseModel):
    """A compiled evidence package for filing a complaint."""

    id: str = Field(default_factory=generate_id)
    decision_id: str
    username: str
    comment_ids: list[str]
    screenshots: list[str] = Field(default_factory=list)
    report_path: str | None = None
    complaint_text: str | None = None
    legal_sections: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
    compiled_at: str = Field(default_factory=utc_now_iso)

    def to_db_dict(self) -> dict:
        return {
            "id": self.id,
            "decision_id": self.decision_id,
            "username": self.username,
            "comment_ids": self.comment_ids,
            "screenshots": self.screenshots,
            "report_path": self.report_path,
            "complaint_text": self.complaint_text,
            "legal_sections": self.legal_sections,
            "metadata": self.metadata,
        }
