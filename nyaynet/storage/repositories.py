"""Data Access Layer: repository classes for all entities."""

import json
import sqlite3
from typing import Any

from nyaynet.common.utils import generate_id, utc_now_iso


class BaseRepository:
    """Base repository with common database operations."""

    def __init__(self, db: sqlite3.Connection):
        self._db = db

    def _fetchone(self, query: str, params: tuple = ()) -> dict | None:
        cursor = self._db.execute(query, params)
        row = cursor.fetchone()
        return dict(row) if row else None

    def _fetchall(self, query: str, params: tuple = ()) -> list[dict]:
        cursor = self._db.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


class CommentRepository(BaseRepository):
    """Repository for comments (immutable, INSERT only)."""

    def insert(self, comment: dict) -> str:
        comment_id = comment.get("id") or generate_id()
        self._db.execute(
            """
            INSERT OR IGNORE INTO comments
            (id, instagram_comment_id, instagram_post_id, username, text,
             timestamp, source, raw_data, checksum, ingested_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                comment_id,
                comment.get("instagram_comment_id"),
                comment.get("instagram_post_id"),
                comment["username"],
                comment["text"],
                comment["timestamp"],
                comment["source"],
                json.dumps(comment.get("raw_data", {})),
                comment["checksum"],
                utc_now_iso(),
            ),
        )
        self._db.commit()
        return comment_id

    def get_by_id(self, comment_id: str) -> dict | None:
        return self._fetchone("SELECT * FROM comments WHERE id = ?", (comment_id,))

    def get_by_instagram_id(self, ig_id: str) -> dict | None:
        return self._fetchone(
            "SELECT * FROM comments WHERE instagram_comment_id = ?", (ig_id,)
        )

    def get_by_username(self, username: str, limit: int = 100) -> list[dict]:
        return self._fetchall(
            "SELECT * FROM comments WHERE username = ? ORDER BY timestamp DESC LIMIT ?",
            (username, limit),
        )

    def get_unclassified(self, limit: int = 50) -> list[dict]:
        return self._fetchall(
            """
            SELECT c.* FROM comments c
            LEFT JOIN classification_results cr ON c.id = cr.comment_id
            WHERE cr.id IS NULL
            ORDER BY c.ingested_at ASC LIMIT ?
            """,
            (limit,),
        )

    def exists(self, instagram_comment_id: str) -> bool:
        row = self._fetchone(
            "SELECT 1 FROM comments WHERE instagram_comment_id = ?",
            (instagram_comment_id,),
        )
        return row is not None


class ClassificationRepository(BaseRepository):
    """Repository for classification results."""

    def insert(self, result: dict) -> str:
        result_id = result.get("id") or generate_id()
        self._db.execute(
            """
            INSERT INTO classification_results
            (id, comment_id, method, labels, confidence_scores,
             overall_confidence, is_hateful, reasoning, model_name, classified_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result_id,
                result["comment_id"],
                result["method"],
                json.dumps(result["labels"]),
                json.dumps(result["confidence_scores"]),
                result["overall_confidence"],
                1 if result["is_hateful"] else 0,
                result.get("reasoning"),
                result.get("model_name"),
                utc_now_iso(),
            ),
        )
        self._db.commit()
        return result_id

    def get_by_comment_id(self, comment_id: str) -> dict | None:
        return self._fetchone(
            "SELECT * FROM classification_results WHERE comment_id = ?",
            (comment_id,),
        )

    def get_hateful(self, min_confidence: float = 0.5, limit: int = 100) -> list[dict]:
        return self._fetchall(
            """
            SELECT * FROM classification_results
            WHERE is_hateful = 1 AND overall_confidence >= ?
            ORDER BY overall_confidence DESC LIMIT ?
            """,
            (min_confidence, limit),
        )


class SeverityRepository(BaseRepository):
    """Repository for severity scores."""

    def insert(self, score: dict) -> str:
        score_id = score.get("id") or generate_id()
        self._db.execute(
            """
            INSERT INTO severity_scores
            (id, comment_id, classification_id, raw_score, normalized_score,
             severity_level, weight_breakdown, scored_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                score_id,
                score["comment_id"],
                score["classification_id"],
                score["raw_score"],
                score["normalized_score"],
                score["severity_level"],
                json.dumps(score["weight_breakdown"]),
                utc_now_iso(),
            ),
        )
        self._db.commit()
        return score_id

    def get_by_comment_id(self, comment_id: str) -> dict | None:
        return self._fetchone(
            "SELECT * FROM severity_scores WHERE comment_id = ?", (comment_id,)
        )


class BehaviorRepository(BaseRepository):
    """Repository for user behavior profiles."""

    def upsert(self, profile: dict) -> str:
        profile_id = profile.get("id") or generate_id()
        now = utc_now_iso()
        self._db.execute(
            """
            INSERT INTO user_behavior_profiles
            (id, username, total_comments, offensive_comments, offense_rate,
             repeat_offender_score, escalation_trend, first_seen, last_seen,
             label_distribution, severity_history, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(username) DO UPDATE SET
                total_comments = excluded.total_comments,
                offensive_comments = excluded.offensive_comments,
                offense_rate = excluded.offense_rate,
                repeat_offender_score = excluded.repeat_offender_score,
                escalation_trend = excluded.escalation_trend,
                last_seen = excluded.last_seen,
                label_distribution = excluded.label_distribution,
                severity_history = excluded.severity_history,
                updated_at = excluded.updated_at
            """,
            (
                profile_id,
                profile["username"],
                profile.get("total_comments", 0),
                profile.get("offensive_comments", 0),
                profile.get("offense_rate", 0.0),
                profile.get("repeat_offender_score", 0.0),
                profile.get("escalation_trend", 0.0),
                profile.get("first_seen", now),
                profile.get("last_seen", now),
                json.dumps(profile.get("label_distribution", {})),
                json.dumps(profile.get("severity_history", [])),
                now,
            ),
        )
        self._db.commit()
        return profile_id

    def get_by_username(self, username: str) -> dict | None:
        return self._fetchone(
            "SELECT * FROM user_behavior_profiles WHERE username = ?",
            (username,),
        )

    def get_repeat_offenders(self, min_score: float = 0.5) -> list[dict]:
        return self._fetchall(
            """
            SELECT * FROM user_behavior_profiles
            WHERE repeat_offender_score >= ?
            ORDER BY repeat_offender_score DESC
            """,
            (min_score,),
        )


class DecisionRepository(BaseRepository):
    """Repository for decisions."""

    def insert(self, decision: dict) -> str:
        decision_id = decision.get("id") or generate_id()
        self._db.execute(
            """
            INSERT INTO decisions
            (id, comment_id, username, action, confidence, severity_level,
             reasoning, rule_triggers, cooldown_until, requires_human_approval,
             human_approved, approved_by, approved_at, decided_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                decision_id,
                decision["comment_id"],
                decision["username"],
                decision["action"],
                decision["confidence"],
                decision.get("severity_level"),
                decision["reasoning"],
                json.dumps(decision.get("rule_triggers", [])),
                decision.get("cooldown_until"),
                1 if decision.get("requires_human_approval", True) else 0,
                None,
                None,
                None,
                utc_now_iso(),
            ),
        )
        self._db.commit()
        return decision_id

    def get_by_id(self, decision_id: str) -> dict | None:
        return self._fetchone(
            "SELECT * FROM decisions WHERE id = ?", (decision_id,)
        )

    def get_pending_review(self) -> list[dict]:
        return self._fetchall(
            """
            SELECT d.*, c.text as comment_text FROM decisions d
            JOIN comments c ON d.comment_id = c.id
            WHERE d.requires_human_approval = 1 AND d.human_approved IS NULL
            AND d.action IN ('recommend_complaint', 'auto_file_complaint')
            ORDER BY d.decided_at DESC
            """
        )

    def approve(self, decision_id: str, approved_by: str = "human") -> None:
        self._db.execute(
            """
            UPDATE decisions SET human_approved = 1, approved_by = ?, approved_at = ?
            WHERE id = ?
            """,
            (approved_by, utc_now_iso(), decision_id),
        )
        self._db.commit()

    def reject(self, decision_id: str, approved_by: str = "human") -> None:
        self._db.execute(
            """
            UPDATE decisions SET human_approved = 0, approved_by = ?, approved_at = ?
            WHERE id = ?
            """,
            (approved_by, utc_now_iso(), decision_id),
        )
        self._db.commit()

    def get_last_action_for_user(self, username: str) -> dict | None:
        return self._fetchone(
            """
            SELECT * FROM decisions WHERE username = ?
            AND action IN ('recommend_complaint', 'auto_file_complaint')
            ORDER BY decided_at DESC LIMIT 1
            """,
            (username,),
        )


class EvidenceRepository(BaseRepository):
    """Repository for evidence packages."""

    def insert(self, package: dict) -> str:
        package_id = package.get("id") or generate_id()
        self._db.execute(
            """
            INSERT INTO evidence_packages
            (id, decision_id, username, comment_ids, screenshots, report_path,
             complaint_text, legal_sections, metadata, compiled_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                package_id,
                package["decision_id"],
                package["username"],
                json.dumps(package["comment_ids"]),
                json.dumps(package.get("screenshots", [])),
                package.get("report_path"),
                package.get("complaint_text"),
                json.dumps(package.get("legal_sections", [])),
                json.dumps(package.get("metadata", {})),
                utc_now_iso(),
            ),
        )
        self._db.commit()
        return package_id

    def get_by_id(self, package_id: str) -> dict | None:
        return self._fetchone(
            "SELECT * FROM evidence_packages WHERE id = ?", (package_id,)
        )

    def get_by_decision_id(self, decision_id: str) -> dict | None:
        return self._fetchone(
            "SELECT * FROM evidence_packages WHERE decision_id = ?",
            (decision_id,),
        )


class ComplaintRepository(BaseRepository):
    """Repository for complaints."""

    def insert(self, complaint: dict) -> str:
        complaint_id = complaint.get("id") or generate_id()
        now = utc_now_iso()
        self._db.execute(
            """
            INSERT INTO complaints
            (id, evidence_package_id, portal_complaint_id, status,
             submission_data, portal_response, confirmation_screenshot,
             filed_at, last_checked, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                complaint_id,
                complaint["evidence_package_id"],
                complaint.get("portal_complaint_id"),
                complaint["status"],
                json.dumps(complaint.get("submission_data", {})),
                complaint.get("portal_response"),
                complaint.get("confirmation_screenshot"),
                complaint.get("filed_at"),
                None,
                now,
            ),
        )
        self._db.commit()
        return complaint_id

    def get_by_id(self, complaint_id: str) -> dict | None:
        return self._fetchone(
            "SELECT * FROM complaints WHERE id = ?", (complaint_id,)
        )

    def update_status(self, complaint_id: str, status: str, **kwargs: Any) -> None:
        sets = ["status = ?", "updated_at = ?"]
        params: list[Any] = [status, utc_now_iso()]

        for key in ("portal_complaint_id", "portal_response",
                     "confirmation_screenshot", "filed_at", "last_checked"):
            if key in kwargs:
                sets.append(f"{key} = ?")
                params.append(kwargs[key])

        params.append(complaint_id)
        self._db.execute(
            f"UPDATE complaints SET {', '.join(sets)} WHERE id = ?",
            tuple(params),
        )
        self._db.commit()

    def get_active(self) -> list[dict]:
        return self._fetchall(
            """
            SELECT * FROM complaints
            WHERE status NOT IN ('resolved', 'rejected', 'filing_failed')
            ORDER BY updated_at DESC
            """
        )


class AuditRepository(BaseRepository):
    """Repository for audit log entries."""

    def get_recent(self, limit: int = 50) -> list[dict]:
        return self._fetchall(
            "SELECT * FROM audit_log ORDER BY rowid DESC LIMIT ?",
            (limit,),
        )

    def get_by_entity(self, entity_type: str, entity_id: str) -> list[dict]:
        return self._fetchall(
            """
            SELECT * FROM audit_log
            WHERE entity_type = ? AND entity_id = ?
            ORDER BY rowid ASC
            """,
            (entity_type, entity_id),
        )
