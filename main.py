"""NyayNet CLI - Autonomous harassment detection and complaint filing agent."""

import sys

import click

from config.logging_config import get_logger, setup_logging
from config.settings import get_settings

log = get_logger(__name__)


def _init_components():
    """Initialize all NyayNet components."""
    settings = get_settings()

    # Database
    from nyaynet.storage.database import init_database
    db = init_database(settings.database_path)

    # Repositories
    from nyaynet.storage.repositories import (
        BehaviorRepository,
        ClassificationRepository,
        CommentRepository,
        ComplaintRepository,
        DecisionRepository,
        EvidenceRepository,
        SeverityRepository,
    )
    comment_repo = CommentRepository(db)
    classification_repo = ClassificationRepository(db)
    severity_repo = SeverityRepository(db)
    behavior_repo = BehaviorRepository(db)
    decision_repo = DecisionRepository(db)
    evidence_repo = EvidenceRepository(db)
    complaint_repo = ComplaintRepository(db)

    # Audit logger
    from nyaynet.common.audit_logger import AuditLogger
    audit_logger = AuditLogger(db)

    # File store
    from nyaynet.storage.file_store import FileStore
    file_store = FileStore(settings.evidence_dir)

    # Ingestion client
    if settings.use_mock_client:
        from nyaynet.ingestion.mock_client import MockInstagramClient
        client = MockInstagramClient()
    else:
        from nyaynet.ingestion.instagram_client import InstagramGraphClient
        client = InstagramGraphClient(
            settings.instagram_access_token,
            settings.instagram_business_account_id,
        )

    # Comment poller
    from nyaynet.ingestion.comment_poller import CommentPoller
    poller = CommentPoller(client, comment_repo, audit_logger)

    # Detection
    from nyaynet.detection.text_preprocessor import TextPreprocessor
    from nyaynet.detection.local_classifier import LocalClassifier
    preprocessor = TextPreprocessor()
    local_classifier = LocalClassifier(settings.local_model_name)

    llm_classifier = None
    if settings.anthropic_api_key:
        from nyaynet.detection.llm_classifier import LLMClassifier
        llm_classifier = LLMClassifier(
            settings.anthropic_api_key,
            settings.claude_model,
            settings.claude_max_tokens,
        )

    from nyaynet.detection.hybrid_engine import HybridDetectionEngine
    detection_engine = HybridDetectionEngine(
        settings, local_classifier, llm_classifier,
        preprocessor, classification_repo, audit_logger,
    )

    # Scoring
    from nyaynet.scoring.severity_scorer import SeverityScorer
    from nyaynet.scoring.behavioral_analyzer import BehavioralAnalyzer
    severity_scorer = SeverityScorer(severity_repo)
    behavioral_analyzer = BehavioralAnalyzer(behavior_repo)

    # Decision
    from nyaynet.decision.decision_engine import DecisionEngine
    from nyaynet.decision.human_override import HumanReviewQueue
    decision_engine = DecisionEngine(settings, decision_repo, audit_logger)
    review_queue = HumanReviewQueue(decision_repo, audit_logger)

    # Evidence
    from nyaynet.evidence.evidence_compiler import EvidenceCompiler
    from nyaynet.evidence.report_generator import ReportGenerator
    evidence_compiler = EvidenceCompiler(
        comment_repo, classification_repo, severity_repo,
        decision_repo, evidence_repo, audit_logger,
    )
    report_generator = ReportGenerator(
        file_store, comment_repo, classification_repo, severity_repo,
    )

    # Filing
    from nyaynet.filing.portal_automator import PortalAutomator
    portal_automator = PortalAutomator(
        settings, complaint_repo, file_store, audit_logger,
    )

    # Tracking
    from nyaynet.tracking.complaint_tracker import ComplaintTracker
    from nyaynet.tracking.notifier import Notifier
    complaint_tracker = ComplaintTracker(complaint_repo, audit_logger)
    notifier = Notifier(settings)

    return {
        "settings": settings,
        "db": db,
        "repos": {
            "comment": comment_repo,
            "classification": classification_repo,
            "severity": severity_repo,
            "behavior": behavior_repo,
            "decision": decision_repo,
            "evidence": evidence_repo,
            "complaint": complaint_repo,
        },
        "audit_logger": audit_logger,
        "file_store": file_store,
        "poller": poller,
        "detection_engine": detection_engine,
        "severity_scorer": severity_scorer,
        "behavioral_analyzer": behavioral_analyzer,
        "decision_engine": decision_engine,
        "review_queue": review_queue,
        "evidence_compiler": evidence_compiler,
        "report_generator": report_generator,
        "portal_automator": portal_automator,
        "complaint_tracker": complaint_tracker,
        "notifier": notifier,
    }


@click.group()
@click.option("--log-level", default="INFO", help="Logging level")
def cli(log_level):
    """NyayNet - Autonomous harassment detection and complaint filing agent."""
    setup_logging(level=log_level)


@cli.command()
def init():
    """Initialize the database and data directories."""
    settings = get_settings()
    setup_logging(level="INFO")

    from pathlib import Path
    for dir_path in [settings.evidence_dir, settings.logs_dir, settings.models_dir]:
        Path(dir_path).mkdir(parents=True, exist_ok=True)

    from nyaynet.storage.database import init_database
    init_database(settings.database_path)

    click.echo("NyayNet initialized successfully.")
    click.echo(f"  Database: {settings.database_path}")
    click.echo(f"  Evidence: {settings.evidence_dir}")
    click.echo(f"  Logs:     {settings.logs_dir}")


@cli.command()
def seed():
    """Seed the database with mock data."""
    setup_logging(level="INFO")
    components = _init_components()
    poller = components["poller"]

    click.echo("Seeding database with mock comments...")
    new_comments = poller.poll_once()
    click.echo(f"  Ingested {len(new_comments)} mock comments.")


@cli.command()
@click.option("--once", is_flag=True, help="Run one monitoring cycle and exit")
@click.option("--post-id", default=None, help="Monitor specific post ID")
def monitor(once, post_id):
    """Monitor Instagram comments for harassment."""
    setup_logging(level="INFO")
    components = _init_components()

    poller = components["poller"]
    detection_engine = components["detection_engine"]
    severity_scorer = components["severity_scorer"]
    behavioral_analyzer = components["behavioral_analyzer"]
    decision_engine = components["decision_engine"]
    notifier = components["notifier"]

    click.echo("Starting harassment monitoring...")

    # Step 1: Ingest new comments
    new_comments = poller.poll_once(post_id=post_id)
    click.echo(f"  Ingested {len(new_comments)} new comments.")

    if not new_comments:
        click.echo("  No new comments to process.")
        if once:
            return

    # Step 2: Classify each comment
    hateful_count = 0
    decisions_made = []

    for comment in new_comments:
        # Classify
        classification = detection_engine.classify(comment.id, comment.text)

        if not classification.is_hateful:
            continue

        hateful_count += 1

        # Score severity
        severity = severity_scorer.score(classification)

        # Update behavior profile
        behavior = behavioral_analyzer.update_profile(
            comment.username, classification, severity,
        )

        # Make decision
        decision = decision_engine.decide(
            classification, severity, behavior, comment.username,
        )
        decisions_made.append(decision)

        # Notify if pending review
        if decision.requires_human_approval and decision.action.value in (
            "recommend_complaint", "auto_file_complaint"
        ):
            notifier.notify_decision_pending(
                decision.id, comment.username, decision.action.value,
            )

    click.echo(f"  Classified {len(new_comments)} comments: {hateful_count} hateful.")
    click.echo(f"  Made {len(decisions_made)} decisions.")

    # Summary of actions
    action_counts: dict[str, int] = {}
    for d in decisions_made:
        action_counts[d.action.value] = action_counts.get(d.action.value, 0) + 1

    for action, count in action_counts.items():
        click.echo(f"    {action}: {count}")

    if not once:
        click.echo("\nContinuous monitoring not yet implemented. Use --once for single cycle.")


@cli.command()
def review():
    """Review pending decisions that require human approval."""
    setup_logging(level="INFO")
    components = _init_components()
    review_queue = components["review_queue"]
    review_queue.review_interactive()


@cli.command("file-complaint")
@click.argument("decision_id")
def file_complaint(decision_id):
    """Compile evidence and file a complaint for a decision."""
    setup_logging(level="INFO")
    components = _init_components()

    decision_repo = components["repos"]["decision"]
    evidence_compiler = components["evidence_compiler"]
    report_generator = components["report_generator"]
    portal_automator = components["portal_automator"]

    # Verify decision exists and is approved
    decision = decision_repo.get_by_id(decision_id)
    if not decision:
        click.echo(f"Decision {decision_id} not found.")
        sys.exit(1)

    if decision.get("requires_human_approval") and not decision.get("human_approved"):
        click.echo("This decision requires human approval. Run 'review' first.")
        sys.exit(1)

    click.echo(f"Compiling evidence for decision {decision_id}...")

    # Compile evidence
    package = evidence_compiler.compile(decision_id)
    click.echo(f"  Evidence package created: {package.id}")
    click.echo(f"  Offensive comments: {len(package.comment_ids)}")
    click.echo(f"  Legal sections: {len(package.legal_sections)}")

    # Generate PDF report
    report_path = report_generator.generate(package)
    click.echo(f"  Report generated: {report_path}")
    package.report_path = report_path

    # File on portal
    click.echo("\nFiling complaint on cybercrime.gov.in...")
    result = portal_automator.file_complaint(package)

    if result.status.value == "filed":
        click.echo(f"\nComplaint filed successfully!")
        click.echo(f"  Portal Complaint ID: {result.portal_complaint_id or 'Pending'}")
        click.echo(f"  Confirmation: {result.confirmation_screenshot or 'N/A'}")
    else:
        click.echo(f"\nFiling failed: {result.portal_response}")
        click.echo("You can retry later or file manually.")


@cli.command()
@click.argument("complaint_id", required=False)
def status(complaint_id):
    """Check complaint status."""
    setup_logging(level="INFO")
    components = _init_components()
    tracker = components["complaint_tracker"]

    if complaint_id:
        complaint = tracker.get_complaint(complaint_id)
        if complaint:
            click.echo(f"Complaint ID: {complaint['id']}")
            click.echo(f"Status:       {complaint['status']}")
            click.echo(f"Portal ID:    {complaint.get('portal_complaint_id', 'N/A')}")
            click.echo(f"Filed at:     {complaint.get('filed_at', 'N/A')}")
            click.echo(f"Updated at:   {complaint['updated_at']}")
        else:
            click.echo(f"Complaint {complaint_id} not found.")
    else:
        summary = tracker.get_summary()
        if summary:
            click.echo("Complaint Summary:")
            for s, count in summary.items():
                click.echo(f"  {s}: {count}")
        else:
            click.echo("No active complaints.")


@cli.command()
def audit():
    """View recent audit log entries."""
    setup_logging(level="INFO")
    components = _init_components()
    audit_logger = components["audit_logger"]

    click.echo("Verifying audit chain integrity...")
    is_valid = audit_logger.verify_chain()
    click.echo(f"  Audit chain valid: {is_valid}")

    from nyaynet.storage.repositories import AuditRepository
    audit_repo = AuditRepository(components["db"])
    entries = audit_repo.get_recent(limit=20)

    if entries:
        click.echo(f"\nLast {len(entries)} audit entries:")
        for entry in entries:
            click.echo(
                f"  [{entry['timestamp']}] {entry['action']} "
                f"({entry['entity_type']}/{entry['entity_id'][:8]}...) "
                f"by {entry['actor']}"
            )
    else:
        click.echo("No audit entries found.")


if __name__ == "__main__":
    cli()
