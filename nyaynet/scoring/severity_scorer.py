"""Weighted severity scoring for classified comments."""

from config.constants import (
    SEVERITY_THRESHOLDS,
    SEVERITY_WEIGHTS,
    DetectionLabel,
    SeverityLevel,
)
from config.logging_config import get_logger
from nyaynet.detection.models import ClassificationResult
from nyaynet.scoring.models import SeverityResult
from nyaynet.storage.repositories import SeverityRepository

log = get_logger(__name__)

# Maximum possible raw score (all categories at max weight)
MAX_RAW_SCORE = max(SEVERITY_WEIGHTS.values())


class SeverityScorer:
    """Computes weighted severity scores for classified comments."""

    def __init__(self, severity_repo: SeverityRepository):
        self._repo = severity_repo

    def score(self, classification: ClassificationResult) -> SeverityResult:
        """Compute severity score based on classification labels and confidence scores.

        Formula: weighted sum of (label_weight * label_confidence)
        Normalized to 0-1 scale.
        """
        weight_breakdown = {}
        raw_score = 0.0

        for label in classification.labels:
            weight = SEVERITY_WEIGHTS.get(label, 0)
            # Use the specific label confidence if available, otherwise overall
            label_key = label.value
            confidence = classification.confidence_scores.get(
                label_key, classification.overall_confidence
            )
            weighted = weight * confidence
            weight_breakdown[label_key] = weighted
            raw_score += weighted

        # Normalize to 0-1 scale
        normalized = min(raw_score / MAX_RAW_SCORE, 1.0) if MAX_RAW_SCORE > 0 else 0.0

        # Determine severity level
        severity_level = self._get_severity_level(normalized)

        result = SeverityResult(
            comment_id=classification.comment_id,
            classification_id=classification.id,
            raw_score=raw_score,
            normalized_score=normalized,
            severity_level=severity_level,
            weight_breakdown=weight_breakdown,
        )

        # Persist
        self._repo.insert(result.to_db_dict())

        log.info(
            "severity_scored",
            comment_id=classification.comment_id,
            raw_score=raw_score,
            normalized=normalized,
            severity=severity_level.value,
        )

        return result

    def _get_severity_level(self, normalized_score: float) -> SeverityLevel:
        """Map normalized score to severity level."""
        if normalized_score >= SEVERITY_THRESHOLDS[SeverityLevel.CRITICAL]:
            return SeverityLevel.CRITICAL
        if normalized_score >= SEVERITY_THRESHOLDS[SeverityLevel.HIGH]:
            return SeverityLevel.HIGH
        if normalized_score >= SEVERITY_THRESHOLDS[SeverityLevel.MODERATE]:
            return SeverityLevel.MODERATE
        if normalized_score >= SEVERITY_THRESHOLDS[SeverityLevel.LOW]:
            return SeverityLevel.LOW
        return SeverityLevel.LOW
