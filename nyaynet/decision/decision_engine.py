"""Rule engine: threshold checks, cooldowns, reasoning generation."""

from datetime import datetime, timedelta, timezone

from config.constants import DecisionAction, SeverityLevel
from config.logging_config import get_logger
from config.settings import Settings
from nyaynet.common.audit_logger import AuditLogger
from nyaynet.common.utils import utc_now_iso
from nyaynet.decision.models import Decision
from nyaynet.detection.models import ClassificationResult
from nyaynet.scoring.models import BehaviorProfile, SeverityResult
from nyaynet.storage.repositories import DecisionRepository

log = get_logger(__name__)


class DecisionEngine:
    """Rule-based decision engine for determining actions on flagged content."""

    def __init__(
        self,
        settings: Settings,
        decision_repo: DecisionRepository,
        audit_logger: AuditLogger,
    ):
        self._settings = settings
        self._repo = decision_repo
        self._audit = audit_logger

    def decide(
        self,
        classification: ClassificationResult,
        severity: SeverityResult,
        behavior: BehaviorProfile,
        username: str,
    ) -> Decision:
        """Apply rules to determine what action to take."""
        rule_triggers = []
        reasoning_parts = []

        # Rule 1: Non-hateful -> IGNORE
        if not classification.is_hateful:
            return self._make_decision(
                comment_id=classification.comment_id,
                username=username,
                action=DecisionAction.IGNORE,
                confidence=classification.overall_confidence,
                severity_level=severity.severity_level,
                reasoning="Comment classified as non-hateful.",
                rule_triggers=["non_hateful"],
            )

        # Rule 2: Low severity -> FLAG for monitoring
        if severity.severity_level == SeverityLevel.LOW:
            rule_triggers.append("low_severity")
            reasoning_parts.append(
                f"Low severity ({severity.normalized_score:.2f}), flagged for monitoring."
            )
            return self._make_decision(
                comment_id=classification.comment_id,
                username=username,
                action=DecisionAction.FLAG,
                confidence=classification.overall_confidence,
                severity_level=severity.severity_level,
                reasoning=" ".join(reasoning_parts),
                rule_triggers=rule_triggers,
            )

        # Rule 3: Check cooldown
        if self._is_on_cooldown(username):
            rule_triggers.append("cooldown_active")
            reasoning_parts.append(
                f"User {username} is within cooldown period. Flagging only."
            )
            return self._make_decision(
                comment_id=classification.comment_id,
                username=username,
                action=DecisionAction.FLAG,
                confidence=classification.overall_confidence,
                severity_level=severity.severity_level,
                reasoning=" ".join(reasoning_parts),
                rule_triggers=rule_triggers,
            )

        # Rule 4: Moderate severity -> WARN
        if severity.severity_level == SeverityLevel.MODERATE:
            rule_triggers.append("moderate_severity")
            reasoning_parts.append(
                f"Moderate severity ({severity.normalized_score:.2f})."
            )

            # Unless repeat offender with enough offensive comments
            if (
                behavior.offensive_comments >= self._settings.min_offensive_comments
                and behavior.repeat_offender_score >= 0.5
            ):
                rule_triggers.append("repeat_offender")
                reasoning_parts.append(
                    f"Repeat offender (score: {behavior.repeat_offender_score:.2f}, "
                    f"offenses: {behavior.offensive_comments}). Recommending complaint."
                )
                return self._make_complaint_decision(
                    classification, severity, behavior, username,
                    rule_triggers, reasoning_parts,
                )

            return self._make_decision(
                comment_id=classification.comment_id,
                username=username,
                action=DecisionAction.WARN,
                confidence=classification.overall_confidence,
                severity_level=severity.severity_level,
                reasoning=" ".join(reasoning_parts),
                rule_triggers=rule_triggers,
            )

        # Rule 5: High/Critical severity
        if severity.severity_level in (SeverityLevel.HIGH, SeverityLevel.CRITICAL):
            rule_triggers.append(f"{severity.severity_level.value}_severity")
            reasoning_parts.append(
                f"{severity.severity_level.value.title()} severity "
                f"({severity.normalized_score:.2f})."
            )

            # Check minimum offensive comments threshold
            if behavior.offensive_comments >= self._settings.min_offensive_comments:
                rule_triggers.append("min_offenses_met")
                reasoning_parts.append(
                    f"User has {behavior.offensive_comments} offensive comments "
                    f"(minimum: {self._settings.min_offensive_comments})."
                )
                return self._make_complaint_decision(
                    classification, severity, behavior, username,
                    rule_triggers, reasoning_parts,
                )
            else:
                rule_triggers.append("min_offenses_not_met")
                reasoning_parts.append(
                    f"User has only {behavior.offensive_comments} offensive comments "
                    f"(need {self._settings.min_offensive_comments}). Warning only."
                )
                return self._make_decision(
                    comment_id=classification.comment_id,
                    username=username,
                    action=DecisionAction.WARN,
                    confidence=classification.overall_confidence,
                    severity_level=severity.severity_level,
                    reasoning=" ".join(reasoning_parts),
                    rule_triggers=rule_triggers,
                )

        # Default: FLAG
        return self._make_decision(
            comment_id=classification.comment_id,
            username=username,
            action=DecisionAction.FLAG,
            confidence=classification.overall_confidence,
            severity_level=severity.severity_level,
            reasoning="Default: flagged for review.",
            rule_triggers=["default"],
        )

    def _make_complaint_decision(
        self,
        classification: ClassificationResult,
        severity: SeverityResult,
        behavior: BehaviorProfile,
        username: str,
        rule_triggers: list[str],
        reasoning_parts: list[str],
    ) -> Decision:
        """Create a complaint recommendation/auto-file decision."""
        # Check confidence threshold
        if classification.overall_confidence >= self._settings.decision_confidence_threshold:
            rule_triggers.append("confidence_met")

            if self._settings.require_human_approval:
                action = DecisionAction.RECOMMEND_COMPLAINT
                reasoning_parts.append("Human approval required before filing.")
            else:
                action = DecisionAction.AUTO_FILE_COMPLAINT
                reasoning_parts.append("Auto-filing enabled.")
        else:
            rule_triggers.append("confidence_not_met")
            reasoning_parts.append(
                f"Confidence {classification.overall_confidence:.2f} below threshold "
                f"{self._settings.decision_confidence_threshold}. Flagging only."
            )
            action = DecisionAction.FLAG

        # Set cooldown
        cooldown_until = (
            datetime.now(timezone.utc)
            + timedelta(hours=self._settings.cooldown_hours)
        ).isoformat()

        return self._make_decision(
            comment_id=classification.comment_id,
            username=username,
            action=action,
            confidence=classification.overall_confidence,
            severity_level=severity.severity_level,
            reasoning=" ".join(reasoning_parts),
            rule_triggers=rule_triggers,
            cooldown_until=cooldown_until,
        )

    def _make_decision(self, **kwargs) -> Decision:
        """Create a decision, persist it, and log it."""
        requires_human = kwargs.get("requires_human_approval")
        if requires_human is None:
            action = kwargs.get("action")
            requires_human = action in (
                DecisionAction.RECOMMEND_COMPLAINT,
                DecisionAction.AUTO_FILE_COMPLAINT,
            ) and self._settings.require_human_approval

        decision = Decision(
            requires_human_approval=requires_human,
            **kwargs,
        )

        self._repo.insert(decision.to_db_dict())

        self._audit.log(
            action="decision_made",
            entity_type="decision",
            entity_id=decision.id,
            details={
                "comment_id": decision.comment_id,
                "username": decision.username,
                "action": decision.action.value,
                "confidence": decision.confidence,
                "rule_triggers": decision.rule_triggers,
            },
        )

        log.info(
            "decision_made",
            decision_id=decision.id,
            username=decision.username,
            action=decision.action.value,
            confidence=decision.confidence,
        )

        return decision

    def _is_on_cooldown(self, username: str) -> bool:
        """Check if a user is within the cooldown period."""
        last_action = self._repo.get_last_action_for_user(username)
        if not last_action or not last_action.get("cooldown_until"):
            return False

        cooldown_until = datetime.fromisoformat(last_action["cooldown_until"])
        return datetime.now(timezone.utc) < cooldown_until
