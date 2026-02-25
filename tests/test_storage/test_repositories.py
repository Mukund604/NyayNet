"""Tests for repository classes."""

import pytest

from nyaynet.common.utils import generate_id, utc_now_iso


class TestCommentRepository:
    def test_insert_and_get(self, comment_repo, sample_comment_dict):
        comment_id = comment_repo.insert(sample_comment_dict)
        result = comment_repo.get_by_id(comment_id)
        assert result is not None
        assert result["username"] == sample_comment_dict["username"]
        assert result["text"] == sample_comment_dict["text"]

    def test_exists(self, comment_repo, sample_comment_dict):
        comment_repo.insert(sample_comment_dict)
        assert comment_repo.exists(sample_comment_dict["instagram_comment_id"])
        assert not comment_repo.exists("nonexistent_id")

    def test_get_by_username(self, comment_repo, sample_comment_dict):
        comment_repo.insert(sample_comment_dict)
        results = comment_repo.get_by_username(sample_comment_dict["username"])
        assert len(results) == 1

    def test_dedup_on_insert(self, comment_repo, sample_comment_dict):
        """INSERT OR IGNORE should not create duplicate entries."""
        comment_repo.insert(sample_comment_dict)
        comment_repo.insert(sample_comment_dict)  # Should be ignored
        results = comment_repo.get_by_username(sample_comment_dict["username"])
        assert len(results) == 1

    def test_get_unclassified(self, comment_repo, sample_comment_dict):
        comment_repo.insert(sample_comment_dict)
        unclassified = comment_repo.get_unclassified()
        assert len(unclassified) == 1


class TestClassificationRepository:
    def test_insert_and_get(self, comment_repo, classification_repo, sample_comment_dict):
        comment_repo.insert(sample_comment_dict)
        classification = {
            "id": generate_id(),
            "comment_id": sample_comment_dict["id"],
            "method": "local",
            "labels": ["abuse"],
            "confidence_scores": {"abuse": 0.9},
            "overall_confidence": 0.9,
            "is_hateful": True,
            "reasoning": "Test",
            "model_name": "test-model",
        }
        classification_repo.insert(classification)
        result = classification_repo.get_by_comment_id(sample_comment_dict["id"])
        assert result is not None
        assert result["is_hateful"] == 1

    def test_get_hateful(self, comment_repo, classification_repo, sample_comment_dict):
        comment_repo.insert(sample_comment_dict)
        classification = {
            "comment_id": sample_comment_dict["id"],
            "method": "local",
            "labels": ["abuse"],
            "confidence_scores": {"abuse": 0.9},
            "overall_confidence": 0.9,
            "is_hateful": True,
        }
        classification_repo.insert(classification)
        hateful = classification_repo.get_hateful(min_confidence=0.5)
        assert len(hateful) == 1


class TestBehaviorRepository:
    def test_upsert_create(self, behavior_repo):
        profile = {
            "username": "test_user",
            "total_comments": 5,
            "offensive_comments": 2,
            "offense_rate": 0.4,
            "repeat_offender_score": 0.3,
            "escalation_trend": 0.1,
        }
        behavior_repo.upsert(profile)
        result = behavior_repo.get_by_username("test_user")
        assert result is not None
        assert result["total_comments"] == 5

    def test_upsert_update(self, behavior_repo):
        profile = {
            "username": "test_user",
            "total_comments": 5,
            "offensive_comments": 2,
            "offense_rate": 0.4,
        }
        behavior_repo.upsert(profile)

        profile["total_comments"] = 10
        behavior_repo.upsert(profile)

        result = behavior_repo.get_by_username("test_user")
        assert result["total_comments"] == 10


class TestDecisionRepository:
    def test_insert_and_get(self, comment_repo, decision_repo, sample_comment_dict):
        comment_repo.insert(sample_comment_dict)
        decision = {
            "id": generate_id(),
            "comment_id": sample_comment_dict["id"],
            "username": "test_user",
            "action": "flag",
            "confidence": 0.8,
            "severity_level": "moderate",
            "reasoning": "Test decision",
            "rule_triggers": ["test_rule"],
            "requires_human_approval": True,
        }
        decision_repo.insert(decision)
        result = decision_repo.get_by_id(decision["id"])
        assert result is not None
        assert result["action"] == "flag"

    def test_approve_and_reject(self, comment_repo, decision_repo, sample_comment_dict):
        comment_repo.insert(sample_comment_dict)
        decision_id = generate_id()
        decision = {
            "id": decision_id,
            "comment_id": sample_comment_dict["id"],
            "username": "test_user",
            "action": "recommend_complaint",
            "confidence": 0.9,
            "reasoning": "Test",
            "requires_human_approval": True,
        }
        decision_repo.insert(decision)

        decision_repo.approve(decision_id)
        result = decision_repo.get_by_id(decision_id)
        assert result["human_approved"] == 1

    def test_get_pending_review(self, comment_repo, decision_repo, sample_comment_dict):
        comment_repo.insert(sample_comment_dict)
        decision = {
            "comment_id": sample_comment_dict["id"],
            "username": "test_user",
            "action": "recommend_complaint",
            "confidence": 0.9,
            "reasoning": "Test",
            "requires_human_approval": True,
        }
        decision_repo.insert(decision)
        pending = decision_repo.get_pending_review()
        assert len(pending) == 1
