"""Pydantic models for the scoring module."""

from pydantic import BaseModel, Field

from config.constants import SeverityLevel
from nyaynet.common.utils import generate_id, utc_now_iso


class SeverityResult(BaseModel):
    """Result of severity scoring for a comment."""

    id: str = Field(default_factory=generate_id)
    comment_id: str
    classification_id: str
    raw_score: float
    normalized_score: float
    severity_level: SeverityLevel
    weight_breakdown: dict[str, float]
    scored_at: str = Field(default_factory=utc_now_iso)

    def to_db_dict(self) -> dict:
        return {
            "id": self.id,
            "comment_id": self.comment_id,
            "classification_id": self.classification_id,
            "raw_score": self.raw_score,
            "normalized_score": self.normalized_score,
            "severity_level": self.severity_level.value,
            "weight_breakdown": self.weight_breakdown,
        }


class BehaviorProfile(BaseModel):
    """User behavior profile for repeat offender tracking."""

    id: str = Field(default_factory=generate_id)
    username: str
    total_comments: int = 0
    offensive_comments: int = 0
    offense_rate: float = 0.0
    repeat_offender_score: float = 0.0
    escalation_trend: float = 0.0
    first_seen: str = Field(default_factory=utc_now_iso)
    last_seen: str = Field(default_factory=utc_now_iso)
    label_distribution: dict[str, int] = Field(default_factory=dict)
    severity_history: list[float] = Field(default_factory=list)

    def to_db_dict(self) -> dict:
        return self.model_dump()
