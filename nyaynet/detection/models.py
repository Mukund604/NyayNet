"""Pydantic models for the detection module."""

from pydantic import BaseModel, Field

from config.constants import DetectionLabel
from nyaynet.common.utils import generate_id, utc_now_iso


class ClassificationResult(BaseModel):
    """Result of classifying a comment."""

    id: str = Field(default_factory=generate_id)
    comment_id: str
    method: str  # 'local', 'llm', 'hybrid'
    labels: list[DetectionLabel]
    confidence_scores: dict[str, float]  # label -> score
    overall_confidence: float
    is_hateful: bool
    reasoning: str | None = None
    model_name: str | None = None
    classified_at: str = Field(default_factory=utc_now_iso)

    def to_db_dict(self) -> dict:
        """Convert to a dict suitable for database insertion."""
        return {
            "id": self.id,
            "comment_id": self.comment_id,
            "method": self.method,
            "labels": [l.value for l in self.labels],
            "confidence_scores": self.confidence_scores,
            "overall_confidence": self.overall_confidence,
            "is_hateful": self.is_hateful,
            "reasoning": self.reasoning,
            "model_name": self.model_name,
        }
