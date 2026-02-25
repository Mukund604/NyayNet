"""Manual review queue for human oversight."""

import click

from config.logging_config import get_logger
from nyaynet.common.audit_logger import AuditLogger
from nyaynet.common.utils import truncate_text
from nyaynet.storage.repositories import DecisionRepository

log = get_logger(__name__)


class HumanReviewQueue:
    """Interactive human review for pending decisions."""

    def __init__(
        self,
        decision_repo: DecisionRepository,
        audit_logger: AuditLogger,
    ):
        self._repo = decision_repo
        self._audit = audit_logger

    def get_pending(self) -> list[dict]:
        """Get all decisions pending human review."""
        return self._repo.get_pending_review()

    def review_interactive(self) -> int:
        """Interactive CLI review of pending decisions.

        Returns the number of decisions reviewed.
        """
        pending = self.get_pending()
        if not pending:
            click.echo("No pending decisions to review.")
            return 0

        click.echo(f"\n{'='*60}")
        click.echo(f"  {len(pending)} decision(s) pending review")
        click.echo(f"{'='*60}\n")

        reviewed = 0
        for decision in pending:
            click.echo(f"Decision ID: {decision['id']}")
            click.echo(f"Username:    @{decision['username']}")
            click.echo(f"Action:      {decision['action']}")
            click.echo(f"Confidence:  {decision['confidence']:.2f}")
            click.echo(f"Severity:    {decision.get('severity_level', 'N/A')}")
            click.echo(f"Comment:     {truncate_text(decision.get('comment_text', 'N/A'), 200)}")
            click.echo(f"Reasoning:   {decision['reasoning']}")
            click.echo(f"Decided at:  {decision['decided_at']}")
            click.echo("-" * 40)

            choice = click.prompt(
                "Action",
                type=click.Choice(["approve", "reject", "skip", "quit"]),
                default="skip",
            )

            if choice == "approve":
                self._repo.approve(decision["id"])
                self._audit.log(
                    action="decision_approved",
                    entity_type="decision",
                    entity_id=decision["id"],
                    actor="human",
                    details={"username": decision["username"]},
                )
                click.echo("  -> Approved\n")
                reviewed += 1

            elif choice == "reject":
                self._repo.reject(decision["id"])
                self._audit.log(
                    action="decision_rejected",
                    entity_type="decision",
                    entity_id=decision["id"],
                    actor="human",
                    details={"username": decision["username"]},
                )
                click.echo("  -> Rejected\n")
                reviewed += 1

            elif choice == "quit":
                click.echo("Exiting review.")
                break
            else:
                click.echo("  -> Skipped\n")

        click.echo(f"\nReviewed {reviewed} decision(s).")
        return reviewed
