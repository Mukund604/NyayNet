"""Integration tests for the full NyayNet pipeline (mock data, no external APIs)."""

import pytest

from config.constants import DetectionLabel, SeverityLevel
from config.settings import Settings
from nyaynet.common.audit_logger import AuditLogger
from nyaynet.decision.decision_engine import DecisionEngine
from nyaynet.ingestion.comment_poller import CommentPoller
from nyaynet.ingestion.mock_client import MockInstagramClient
from nyaynet.scoring.behavioral_analyzer import BehavioralAnalyzer
from nyaynet.scoring.severity_scorer import SeverityScorer
from nyaynet.storage.repositories import (
    BehaviorRepository,
    ClassificationRepository,
    CommentRepository,
    DecisionRepository,
    SeverityRepository,
)


@pytest.fixture
def pipeline_components(test_db):
    """Set up all pipeline components with an in-memory database."""
    settings = Settings(
        database_path=":memory:",
        use_mock_client=True,
        require_human_approval=True,
        decision_confidence_threshold=0.85,
        min_offensive_comments=3,
        cooldown_hours=24,
        local_model_hate_threshold_high=0.85,
        local_model_hate_threshold_low=0.4,
    )

    comment_repo = CommentRepository(test_db)
    classification_repo = ClassificationRepository(test_db)
    severity_repo = SeverityRepository(test_db)
    behavior_repo = BehaviorRepository(test_db)
    decision_repo = DecisionRepository(test_db)
    audit_logger = AuditLogger(test_db)

    client = MockInstagramClient()
    poller = CommentPoller(client, comment_repo, audit_logger)
    severity_scorer = SeverityScorer(severity_repo)
    behavioral_analyzer = BehavioralAnalyzer(behavior_repo)
    decision_engine = DecisionEngine(settings, decision_repo, audit_logger)

    return {
        "settings": settings,
        "repos": {
            "comment": comment_repo,
            "classification": classification_repo,
            "severity": severity_repo,
            "behavior": behavior_repo,
            "decision": decision_repo,
        },
        "audit_logger": audit_logger,
        "poller": poller,
        "severity_scorer": severity_scorer,
        "behavioral_analyzer": behavioral_analyzer,
        "decision_engine": decision_engine,
    }


def test_ingestion_pipeline(pipeline_components):
    """Test that mock comments are ingested and persisted."""
    poller = pipeline_components["poller"]
    comment_repo = pipeline_components["repos"]["comment"]

    new_comments = poller.poll_once()
    assert len(new_comments) > 10  # Mock has ~25 comments

    # Verify persistence
    for comment in new_comments[:5]:
        stored = comment_repo.get_by_id(comment.id)
        assert stored is not None


def test_scoring_pipeline(pipeline_components):
    """Test severity scoring with mock data."""
    severity_scorer = pipeline_components["severity_scorer"]

    from nyaynet.detection.models import ClassificationResult

    # Score a threatening comment
    classification = ClassificationResult(
        comment_id="test_threat",
        method="hybrid",
        labels=[DetectionLabel.THREAT, DetectionLabel.ABUSE],
        confidence_scores={"threat": 0.9, "abuse": 0.7},
        overall_confidence=0.85,
        is_hateful=True,
    )

    result = severity_scorer.score(classification)
    assert result.severity_level in (SeverityLevel.HIGH, SeverityLevel.CRITICAL)
    assert result.normalized_score > 0.5


def test_behavioral_analysis_pipeline(pipeline_components):
    """Test behavioral analysis accumulation."""
    analyzer = pipeline_components["behavioral_analyzer"]

    from nyaynet.detection.models import ClassificationResult
    from nyaynet.scoring.models import SeverityResult

    for i in range(5):
        classification = ClassificationResult(
            comment_id=f"c_{i}",
            method="hybrid",
            labels=[DetectionLabel.ABUSE],
            confidence_scores={"abuse": 0.8},
            overall_confidence=0.8,
            is_hateful=True,
        )
        severity = SeverityResult(
            comment_id=f"c_{i}",
            classification_id=classification.id,
            raw_score=2.4,
            normalized_score=0.34,
            severity_level=SeverityLevel.MODERATE,
            weight_breakdown={"abuse": 2.4},
        )
        profile = analyzer.update_profile("repeat_offender", classification, severity)

    assert profile.total_comments == 5
    assert profile.offensive_comments == 5
    assert profile.repeat_offender_score > 0.3


def test_decision_pipeline(pipeline_components):
    """Test decision engine with enough data to trigger complaint recommendation."""
    decision_engine = pipeline_components["decision_engine"]

    from nyaynet.detection.models import ClassificationResult
    from nyaynet.scoring.models import BehaviorProfile, SeverityResult

    classification = ClassificationResult(
        comment_id="severe_comment",
        method="hybrid",
        labels=[DetectionLabel.THREAT],
        confidence_scores={"threat": 0.95},
        overall_confidence=0.95,
        is_hateful=True,
    )
    severity = SeverityResult(
        comment_id="severe_comment",
        classification_id=classification.id,
        raw_score=6.65,
        normalized_score=0.95,
        severity_level=SeverityLevel.CRITICAL,
        weight_breakdown={"threat": 6.65},
    )
    behavior = BehaviorProfile(
        username="dangerous_user",
        total_comments=10,
        offensive_comments=8,
        offense_rate=0.8,
        repeat_offender_score=0.7,
    )

    decision = decision_engine.decide(
        classification, severity, behavior, "dangerous_user"
    )

    # Should recommend complaint (high severity, enough offenses, high confidence)
    assert decision.action.value in ("recommend_complaint", "auto_file_complaint")


def test_audit_chain_integrity(pipeline_components):
    """Test that audit chain maintains integrity through operations."""
    audit_logger = pipeline_components["audit_logger"]
    poller = pipeline_components["poller"]

    # Run ingestion to generate audit entries
    poller.poll_once()

    # Verify chain
    assert audit_logger.verify_chain() is True
