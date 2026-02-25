"""Per-user behavioral analysis: repeat offender score, escalation trends."""

import json

from config.logging_config import get_logger
from nyaynet.common.utils import utc_now_iso
from nyaynet.detection.models import ClassificationResult
from nyaynet.scoring.models import BehaviorProfile, SeverityResult
from nyaynet.storage.repositories import BehaviorRepository

log = get_logger(__name__)

# Keep last N severity scores for trend analysis
MAX_SEVERITY_HISTORY = 50


class BehavioralAnalyzer:
    """Tracks per-user behavior patterns and computes repeat offender scores."""

    def __init__(self, behavior_repo: BehaviorRepository):
        self._repo = behavior_repo

    def update_profile(
        self,
        username: str,
        classification: ClassificationResult,
        severity: SeverityResult,
    ) -> BehaviorProfile:
        """Update or create a user behavior profile based on new classification."""
        # Fetch existing profile or create new
        existing = self._repo.get_by_username(username)

        if existing:
            profile = self._build_from_db(existing)
        else:
            profile = BehaviorProfile(
                username=username,
                first_seen=utc_now_iso(),
            )

        # Update counts
        profile.total_comments += 1
        if classification.is_hateful:
            profile.offensive_comments += 1

        # Update offense rate
        profile.offense_rate = (
            profile.offensive_comments / profile.total_comments
            if profile.total_comments > 0
            else 0.0
        )

        # Update label distribution
        for label in classification.labels:
            label_key = label.value
            profile.label_distribution[label_key] = (
                profile.label_distribution.get(label_key, 0) + 1
            )

        # Update severity history
        profile.severity_history.append(severity.normalized_score)
        if len(profile.severity_history) > MAX_SEVERITY_HISTORY:
            profile.severity_history = profile.severity_history[-MAX_SEVERITY_HISTORY:]

        # Compute repeat offender score
        profile.repeat_offender_score = self._compute_repeat_score(profile)

        # Compute escalation trend
        profile.escalation_trend = self._compute_escalation_trend(profile)

        # Update timestamps
        profile.last_seen = utc_now_iso()

        # Persist
        self._repo.upsert(profile.to_db_dict())

        log.info(
            "behavior_profile_updated",
            username=username,
            total=profile.total_comments,
            offensive=profile.offensive_comments,
            repeat_score=profile.repeat_offender_score,
            escalation=profile.escalation_trend,
        )

        return profile

    def _compute_repeat_score(self, profile: BehaviorProfile) -> float:
        """Compute repeat offender score (0-1).

        Factors:
        - Offense rate (weight: 0.4)
        - Number of offensive comments (weight: 0.3, capped at 10)
        - Severity average (weight: 0.3)
        """
        offense_rate_component = profile.offense_rate * 0.4

        count_component = min(profile.offensive_comments / 10.0, 1.0) * 0.3

        avg_severity = (
            sum(profile.severity_history) / len(profile.severity_history)
            if profile.severity_history
            else 0.0
        )
        severity_component = avg_severity * 0.3

        return min(offense_rate_component + count_component + severity_component, 1.0)

    def _compute_escalation_trend(self, profile: BehaviorProfile) -> float:
        """Compute escalation trend (-1 to 1).

        Positive = escalating severity over time.
        Negative = de-escalating.
        Zero = stable.
        """
        history = profile.severity_history
        if len(history) < 3:
            return 0.0

        # Compare recent half vs older half
        mid = len(history) // 2
        older = history[:mid]
        recent = history[mid:]

        avg_older = sum(older) / len(older) if older else 0.0
        avg_recent = sum(recent) / len(recent) if recent else 0.0

        return max(min(avg_recent - avg_older, 1.0), -1.0)

    def _build_from_db(self, row: dict) -> BehaviorProfile:
        """Build a BehaviorProfile from a database row."""
        label_dist = row.get("label_distribution", "{}")
        if isinstance(label_dist, str):
            label_dist = json.loads(label_dist)

        severity_hist = row.get("severity_history", "[]")
        if isinstance(severity_hist, str):
            severity_hist = json.loads(severity_hist)

        return BehaviorProfile(
            id=row["id"],
            username=row["username"],
            total_comments=row["total_comments"],
            offensive_comments=row["offensive_comments"],
            offense_rate=row["offense_rate"],
            repeat_offender_score=row["repeat_offender_score"],
            escalation_trend=row["escalation_trend"],
            first_seen=row["first_seen"],
            last_seen=row["last_seen"],
            label_distribution=label_dist,
            severity_history=severity_hist,
        )

    def get_profile(self, username: str) -> BehaviorProfile | None:
        """Get a user's behavior profile."""
        row = self._repo.get_by_username(username)
        if row:
            return self._build_from_db(row)
        return None
