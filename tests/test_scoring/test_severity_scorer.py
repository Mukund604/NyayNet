"""Tests for severity scorer."""

from config.constants import DetectionLabel, SeverityLevel
from nyaynet.detection.models import ClassificationResult
from nyaynet.scoring.severity_scorer import SeverityScorer


def test_normal_comment_low_severity(severity_repo):
    scorer = SeverityScorer(severity_repo)
    classification = ClassificationResult(
        comment_id="test_1",
        method="hybrid",
        labels=[DetectionLabel.NORMAL],
        confidence_scores={"normal": 0.95},
        overall_confidence=0.95,
        is_hateful=False,
    )
    result = scorer.score(classification)
    assert result.normalized_score == 0.0
    assert result.severity_level == SeverityLevel.LOW


def test_abuse_moderate_severity(severity_repo):
    scorer = SeverityScorer(severity_repo)
    classification = ClassificationResult(
        comment_id="test_2",
        method="hybrid",
        labels=[DetectionLabel.ABUSE],
        confidence_scores={"abuse": 0.8},
        overall_confidence=0.8,
        is_hateful=True,
    )
    result = scorer.score(classification)
    # abuse weight = 3, confidence 0.8, raw = 2.4, normalized = 2.4/7 ≈ 0.34
    assert result.raw_score > 0
    assert result.normalized_score > 0


def test_threat_high_severity(severity_repo):
    scorer = SeverityScorer(severity_repo)
    classification = ClassificationResult(
        comment_id="test_3",
        method="hybrid",
        labels=[DetectionLabel.THREAT],
        confidence_scores={"threat": 0.95},
        overall_confidence=0.95,
        is_hateful=True,
    )
    result = scorer.score(classification)
    # threat weight = 7, confidence 0.95, raw = 6.65, normalized = 6.65/7 ≈ 0.95
    assert result.severity_level in (SeverityLevel.HIGH, SeverityLevel.CRITICAL)


def test_multiple_labels_compound(severity_repo):
    scorer = SeverityScorer(severity_repo)
    classification = ClassificationResult(
        comment_id="test_4",
        method="hybrid",
        labels=[DetectionLabel.SEXUAL, DetectionLabel.THREAT],
        confidence_scores={"sexual": 0.8, "threat": 0.7},
        overall_confidence=0.75,
        is_hateful=True,
    )
    result = scorer.score(classification)
    # sexual*0.8 + threat*0.7 = 5*0.8 + 7*0.7 = 4.0 + 4.9 = 8.9
    assert result.raw_score > 5
    assert result.weight_breakdown["sexual"] > 0
    assert result.weight_breakdown["threat"] > 0


def test_severity_result_persisted(severity_repo):
    scorer = SeverityScorer(severity_repo)
    classification = ClassificationResult(
        comment_id="test_5",
        method="hybrid",
        labels=[DetectionLabel.ABUSE],
        confidence_scores={"abuse": 0.7},
        overall_confidence=0.7,
        is_hateful=True,
    )
    result = scorer.score(classification)
    stored = severity_repo.get_by_comment_id("test_5")
    assert stored is not None
    assert stored["id"] == result.id
