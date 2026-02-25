"""Aggregate flagged data into evidence packages and generate legal complaint text."""

import json

from config.constants import DetectionLabel
from config.logging_config import get_logger
from nyaynet.common.audit_logger import AuditLogger
from nyaynet.common.utils import utc_now_iso
from nyaynet.evidence.models import EvidencePackage
from nyaynet.storage.repositories import (
    ClassificationRepository,
    CommentRepository,
    DecisionRepository,
    EvidenceRepository,
    SeverityRepository,
)

log = get_logger(__name__)

# Indian legal sections relevant to online harassment
LEGAL_SECTIONS = {
    DetectionLabel.ABUSE: [
        "Section 67 IT Act, 2000 - Publishing obscene material",
        "Section 509 IPC - Word, gesture or act intended to insult the modesty of a woman",
    ],
    DetectionLabel.SEXUAL: [
        "Section 67A IT Act, 2000 - Publishing sexually explicit material",
        "Section 354A IPC - Sexual harassment",
        "Section 509 IPC - Word, gesture or act intended to insult the modesty of a woman",
    ],
    DetectionLabel.THREAT: [
        "Section 506 IPC - Criminal intimidation",
        "Section 507 IPC - Criminal intimidation by anonymous communication",
        "Section 66A IT Act, 2000 - Sending offensive messages",
    ],
    DetectionLabel.DOXXING: [
        "Section 72 IT Act, 2000 - Breach of confidentiality and privacy",
        "Section 66E IT Act, 2000 - Violation of privacy",
    ],
    DetectionLabel.HATE_SPEECH: [
        "Section 153A IPC - Promoting enmity between groups",
        "Section 295A IPC - Deliberate acts to outrage religious feelings",
        "Section 66A IT Act, 2000 - Sending offensive messages",
    ],
}


class EvidenceCompiler:
    """Compiles evidence packages from flagged comments and classifications."""

    def __init__(
        self,
        comment_repo: CommentRepository,
        classification_repo: ClassificationRepository,
        severity_repo: SeverityRepository,
        decision_repo: DecisionRepository,
        evidence_repo: EvidenceRepository,
        audit_logger: AuditLogger,
    ):
        self._comments = comment_repo
        self._classifications = classification_repo
        self._severities = severity_repo
        self._decisions = decision_repo
        self._evidence = evidence_repo
        self._audit = audit_logger

    def compile(self, decision_id: str) -> EvidencePackage:
        """Compile an evidence package for a decision."""
        decision = self._decisions.get_by_id(decision_id)
        if not decision:
            raise ValueError(f"Decision {decision_id} not found")

        username = decision["username"]

        # Gather all offensive comments by this user
        all_comments = self._comments.get_by_username(username)
        offensive_comment_ids = []
        all_labels = set()
        comment_details = []

        for comment in all_comments:
            classification = self._classifications.get_by_comment_id(comment["id"])
            if classification and classification.get("is_hateful"):
                offensive_comment_ids.append(comment["id"])

                labels_data = classification.get("labels", "[]")
                if isinstance(labels_data, str):
                    labels_data = json.loads(labels_data)
                for label in labels_data:
                    try:
                        all_labels.add(DetectionLabel(label))
                    except ValueError:
                        pass

                severity = self._severities.get_by_comment_id(comment["id"])
                comment_details.append({
                    "text": comment["text"],
                    "timestamp": comment["timestamp"],
                    "labels": labels_data,
                    "severity": severity.get("severity_level") if severity else "unknown",
                })

        # Determine applicable legal sections
        legal_sections = []
        for label in all_labels:
            if label in LEGAL_SECTIONS:
                legal_sections.extend(LEGAL_SECTIONS[label])
        legal_sections = list(set(legal_sections))

        # Generate complaint text
        complaint_text = self._generate_complaint_text(
            username, comment_details, legal_sections
        )

        package = EvidencePackage(
            decision_id=decision_id,
            username=username,
            comment_ids=offensive_comment_ids,
            complaint_text=complaint_text,
            legal_sections=legal_sections,
            metadata={
                "total_offensive_comments": len(offensive_comment_ids),
                "labels_found": [l.value for l in all_labels],
                "compiled_at": utc_now_iso(),
            },
        )

        # Persist
        self._evidence.insert(package.to_db_dict())

        self._audit.log(
            action="evidence_compiled",
            entity_type="evidence_package",
            entity_id=package.id,
            details={
                "decision_id": decision_id,
                "username": username,
                "num_comments": len(offensive_comment_ids),
                "legal_sections_count": len(legal_sections),
            },
        )

        log.info(
            "evidence_compiled",
            package_id=package.id,
            username=username,
            num_comments=len(offensive_comment_ids),
        )

        return package

    def _generate_complaint_text(
        self,
        username: str,
        comment_details: list[dict],
        legal_sections: list[str],
    ) -> str:
        """Generate formal complaint text for the portal."""
        lines = [
            "COMPLAINT REGARDING ONLINE HARASSMENT ON INSTAGRAM",
            "",
            f"Subject: Complaint against Instagram user '@{username}' for online harassment",
            "",
            "Respected Sir/Madam,",
            "",
            f"I am writing to file a formal complaint against the Instagram user '@{username}' "
            "for persistent online harassment and cyberbullying on the Instagram platform.",
            "",
            f"The accused user has posted {len(comment_details)} offensive comment(s) "
            "that constitute harassment, as detailed below:",
            "",
        ]

        for i, detail in enumerate(comment_details, 1):
            lines.append(f"  {i}. Comment: \"{detail['text']}\"")
            lines.append(f"     Date/Time: {detail['timestamp']}")
            lines.append(f"     Categories: {', '.join(detail['labels'])}")
            lines.append(f"     Severity: {detail['severity']}")
            lines.append("")

        if legal_sections:
            lines.append("Applicable Legal Provisions:")
            for section in legal_sections:
                lines.append(f"  - {section}")
            lines.append("")

        lines.extend([
            "I request you to kindly take appropriate action against the accused "
            "under the applicable provisions of the Information Technology Act, 2000 "
            "and the Indian Penal Code.",
            "",
            "Evidence including screenshots and detailed analysis report is attached.",
            "",
            "Thank you for your attention to this matter.",
        ])

        return "\n".join(lines)
