"""Tests for behavioral analyzer."""

from config.constants import DetectionLabel, SeverityLevel
from nyaynet.detection.models import ClassificationResult
from nyaynet.scoring.behavioral_analyzer import BehavioralAnalyzer
from nyaynet.scoring.models import SeverityResult


def _make_classification(comment_id, is_hateful=True, labels=None):
    return ClassificationResult(
        comment_id=comment_id,
        method="hybrid",
        labels=labels or [DetectionLabel.ABUSE],
        confidence_scores={"abuse": 0.8},
        overall_confidence=0.8,
        is_hateful=is_hateful,
    )


def _make_severity(comment_id, classification_id, score=0.5):
    return SeverityResult(
        comment_id=comment_id,
        classification_id=classification_id,
        raw_score=score * 7,
        normalized_score=score,
        severity_level=SeverityLevel.MODERATE,
        weight_breakdown={"abuse": score * 3},
    )


def test_create_new_profile(behavior_repo):
    analyzer = BehavioralAnalyzer(behavior_repo)
    classification = _make_classification("c1")
    severity = _make_severity("c1", classification.id)

    profile = analyzer.update_profile("user1", classification, severity)
    assert profile.username == "user1"
    assert profile.total_comments == 1
    assert profile.offensive_comments == 1


def test_update_existing_profile(behavior_repo):
    analyzer = BehavioralAnalyzer(behavior_repo)

    c1 = _make_classification("c1")
    s1 = _make_severity("c1", c1.id)
    analyzer.update_profile("user1", c1, s1)

    c2 = _make_classification("c2")
    s2 = _make_severity("c2", c2.id)
    profile = analyzer.update_profile("user1", c2, s2)

    assert profile.total_comments == 2
    assert profile.offensive_comments == 2


def test_non_hateful_doesnt_increase_offensive(behavior_repo):
    analyzer = BehavioralAnalyzer(behavior_repo)

    c1 = _make_classification("c1", is_hateful=False, labels=[DetectionLabel.NORMAL])
    s1 = _make_severity("c1", c1.id, score=0.0)
    profile = analyzer.update_profile("user1", c1, s1)

    assert profile.total_comments == 1
    assert profile.offensive_comments == 0
    assert profile.offense_rate == 0.0


def test_repeat_offender_score_increases(behavior_repo):
    analyzer = BehavioralAnalyzer(behavior_repo)

    for i in range(5):
        c = _make_classification(f"c{i}")
        s = _make_severity(f"c{i}", c.id, score=0.7)
        profile = analyzer.update_profile("repeat_user", c, s)

    assert profile.repeat_offender_score > 0.3


def test_escalation_trend(behavior_repo):
    analyzer = BehavioralAnalyzer(behavior_repo)

    # Start with low severity
    for i in range(5):
        c = _make_classification(f"c{i}")
        s = _make_severity(f"c{i}", c.id, score=0.2)
        analyzer.update_profile("escalator", c, s)

    # Escalate to high severity
    for i in range(5, 10):
        c = _make_classification(f"c{i}")
        s = _make_severity(f"c{i}", c.id, score=0.9)
        profile = analyzer.update_profile("escalator", c, s)

    assert profile.escalation_trend > 0  # Should show escalation


def test_get_profile(behavior_repo):
    analyzer = BehavioralAnalyzer(behavior_repo)
    c1 = _make_classification("c1")
    s1 = _make_severity("c1", c1.id)
    analyzer.update_profile("findme", c1, s1)

    profile = analyzer.get_profile("findme")
    assert profile is not None
    assert profile.username == "findme"

    assert analyzer.get_profile("nonexistent") is None
