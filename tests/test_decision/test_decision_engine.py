"""Tests for decision engine."""

import pytest

from config.constants import DecisionAction, DetectionLabel, SeverityLevel
from config.settings import Settings
from nyaynet.decision.decision_engine import DecisionEngine
from nyaynet.detection.models import ClassificationResult
from nyaynet.scoring.models import BehaviorProfile, SeverityResult


@pytest.fixture
def engine(decision_repo, audit_logger):
    settings = Settings(
        database_path=":memory:",
        decision_confidence_threshold=0.85,
        min_offensive_comments=3,
        cooldown_hours=24,
        require_human_approval=True,
    )
    return DecisionEngine(settings, decision_repo, audit_logger)


def _make_classification(comment_id, is_hateful, confidence=0.9, labels=None):
    return ClassificationResult(
        comment_id=comment_id,
        method="hybrid",
        labels=labels or ([DetectionLabel.ABUSE] if is_hateful else [DetectionLabel.NORMAL]),
        confidence_scores={"abuse": confidence} if is_hateful else {"normal": confidence},
        overall_confidence=confidence,
        is_hateful=is_hateful,
    )


def _make_severity(comment_id, level, score=0.5):
    return SeverityResult(
        comment_id=comment_id,
        classification_id="cls_1",
        raw_score=score * 7,
        normalized_score=score,
        severity_level=level,
        weight_breakdown={"abuse": score * 3},
    )


def _make_behavior(username, offensive=0, repeat_score=0.0):
    return BehaviorProfile(
        username=username,
        total_comments=max(offensive, 1),
        offensive_comments=offensive,
        offense_rate=offensive / max(offensive, 1),
        repeat_offender_score=repeat_score,
    )


def test_non_hateful_ignored(engine):
    classification = _make_classification("c1", is_hateful=False)
    severity = _make_severity("c1", SeverityLevel.LOW, 0.1)
    behavior = _make_behavior("user1")

    decision = engine.decide(classification, severity, behavior, "user1")
    assert decision.action == DecisionAction.IGNORE


def test_low_severity_flagged(engine):
    classification = _make_classification("c1", is_hateful=True)
    severity = _make_severity("c1", SeverityLevel.LOW, 0.15)
    behavior = _make_behavior("user1", offensive=1)

    decision = engine.decide(classification, severity, behavior, "user1")
    assert decision.action == DecisionAction.FLAG


def test_moderate_severity_warned(engine):
    classification = _make_classification("c1", is_hateful=True)
    severity = _make_severity("c1", SeverityLevel.MODERATE, 0.5)
    behavior = _make_behavior("user1", offensive=1)

    decision = engine.decide(classification, severity, behavior, "user1")
    assert decision.action == DecisionAction.WARN


def test_high_severity_enough_offenses_recommends_complaint(engine):
    classification = _make_classification("c1", is_hateful=True, confidence=0.9)
    severity = _make_severity("c1", SeverityLevel.HIGH, 0.8)
    behavior = _make_behavior("user1", offensive=5, repeat_score=0.6)

    decision = engine.decide(classification, severity, behavior, "user1")
    assert decision.action == DecisionAction.RECOMMEND_COMPLAINT
    assert decision.requires_human_approval


def test_high_severity_insufficient_offenses_warned(engine):
    classification = _make_classification("c1", is_hateful=True, confidence=0.9)
    severity = _make_severity("c1", SeverityLevel.HIGH, 0.8)
    behavior = _make_behavior("user1", offensive=1)

    decision = engine.decide(classification, severity, behavior, "user1")
    assert decision.action == DecisionAction.WARN


def test_confidence_below_threshold_flagged(engine):
    classification = _make_classification("c1", is_hateful=True, confidence=0.7)
    severity = _make_severity("c1", SeverityLevel.HIGH, 0.8)
    behavior = _make_behavior("user1", offensive=5, repeat_score=0.6)

    decision = engine.decide(classification, severity, behavior, "user1")
    assert decision.action == DecisionAction.FLAG
