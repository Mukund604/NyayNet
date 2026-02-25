"""Pydantic models for the decision module."""

from pydantic import BaseModel, Field

from config.constants import DecisionAction, SeverityLevel
from nyaynet.common.utils import generate_id, utc_now_iso


class Decision(BaseModel):
    """A decision about what action to take on a flagged comment/user."""

    id: str = Field(default_factory=generate_id)
    comment_id: str
    username: str
    action: DecisionAction
    confidence: float
    severity_level: SeverityLevel | None = None
    reasoning: str
    rule_triggers: list[str] = Field(default_factory=list)
    cooldown_until: str | None = None
    requires_human_approval: bool = True
    human_approved: bool | None = None
    approved_by: str | None = None
    approved_at: str | None = None
    decided_at: str = Field(default_factory=utc_now_iso)

    def to_db_dict(self) -> dict:
        return {
            "id": self.id,
            "comment_id": self.comment_id,
            "username": self.username,
            "action": self.action.value,
            "confidence": self.confidence,
            "severity_level": self.severity_level.value if self.severity_level else None,
            "reasoning": self.reasoning,
            "rule_triggers": self.rule_triggers,
            "cooldown_until": self.cooldown_until,
            "requires_human_approval": self.requires_human_approval,
        }
