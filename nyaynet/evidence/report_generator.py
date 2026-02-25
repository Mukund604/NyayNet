"""PDF report generation using ReportLab."""

import json
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from config.logging_config import get_logger
from nyaynet.common.exceptions import ReportGenerationError
from nyaynet.evidence.models import EvidencePackage
from nyaynet.storage.file_store import FileStore
from nyaynet.storage.repositories import CommentRepository, ClassificationRepository, SeverityRepository

log = get_logger(__name__)


class ReportGenerator:
    """Generates PDF evidence reports using ReportLab."""

    def __init__(
        self,
        file_store: FileStore,
        comment_repo: CommentRepository,
        classification_repo: ClassificationRepository,
        severity_repo: SeverityRepository,
    ):
        self._file_store = file_store
        self._comment_repo = comment_repo
        self._classification_repo = classification_repo
        self._severity_repo = severity_repo

    def generate(self, package: EvidencePackage) -> str:
        """Generate a PDF report for an evidence package.

        Returns the file path of the generated PDF.
        """
        try:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"report_{package.username}_{timestamp}.pdf"
            file_path = self._file_store._get_user_dir(package.username) / filename

            doc = SimpleDocTemplate(
                str(file_path),
                pagesize=A4,
                rightMargin=0.75 * inch,
                leftMargin=0.75 * inch,
                topMargin=0.75 * inch,
                bottomMargin=0.75 * inch,
            )

            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                "CustomTitle",
                parent=styles["Title"],
                fontSize=16,
                spaceAfter=20,
            )
            heading_style = ParagraphStyle(
                "CustomHeading",
                parent=styles["Heading2"],
                fontSize=12,
                spaceAfter=10,
                spaceBefore=15,
            )

            elements = []

            # Title
            elements.append(
                Paragraph("EVIDENCE REPORT - ONLINE HARASSMENT", title_style)
            )
            elements.append(Paragraph("NyayNet Automated Analysis", styles["Normal"]))
            elements.append(Spacer(1, 20))

            # Summary table
            summary_data = [
                ["Report ID", package.id],
                ["Target User", f"@{package.username}"],
                ["Generated At", datetime.now(timezone.utc).isoformat()],
                ["Total Offensive Comments", str(len(package.comment_ids))],
                ["Decision ID", package.decision_id],
            ]
            summary_table = Table(summary_data, colWidths=[2 * inch, 4 * inch])
            summary_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]))
            elements.append(summary_table)
            elements.append(Spacer(1, 20))

            # Comment details
            elements.append(Paragraph("Flagged Comments", heading_style))

            for comment_id in package.comment_ids:
                comment = self._comment_repo.get_by_id(comment_id)
                if not comment:
                    continue

                classification = self._classification_repo.get_by_comment_id(comment_id)
                severity = self._severity_repo.get_by_comment_id(comment_id)

                labels_str = "N/A"
                if classification:
                    labels_data = classification.get("labels", "[]")
                    if isinstance(labels_data, str):
                        labels_data = json.loads(labels_data)
                    labels_str = ", ".join(labels_data)

                severity_str = severity.get("severity_level", "N/A") if severity else "N/A"

                comment_data = [
                    ["Comment", Paragraph(comment["text"], styles["Normal"])],
                    ["Username", f"@{comment['username']}"],
                    ["Timestamp", comment["timestamp"]],
                    ["Labels", labels_str],
                    ["Severity", severity_str],
                    [
                        "Confidence",
                        f"{classification.get('overall_confidence', 0):.2f}"
                        if classification
                        else "N/A",
                    ],
                ]
                comment_table = Table(comment_data, colWidths=[1.5 * inch, 4.5 * inch])
                comment_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (0, -1), colors.Color(0.95, 0.95, 0.95)),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("PADDING", (0, 0), (-1, -1), 5),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]))
                elements.append(comment_table)
                elements.append(Spacer(1, 10))

            # Legal sections
            if package.legal_sections:
                elements.append(Paragraph("Applicable Legal Provisions", heading_style))
                for section in package.legal_sections:
                    elements.append(
                        Paragraph(f"&bull; {section}", styles["Normal"])
                    )
                elements.append(Spacer(1, 10))

            # Complaint text
            if package.complaint_text:
                elements.append(Paragraph("Complaint Text", heading_style))
                for line in package.complaint_text.split("\n"):
                    if line.strip():
                        elements.append(Paragraph(line, styles["Normal"]))
                    else:
                        elements.append(Spacer(1, 6))

            # Build PDF
            doc.build(elements)

            log.info("report_generated", path=str(file_path), username=package.username)
            return str(file_path)

        except Exception as e:
            raise ReportGenerationError(
                f"Failed to generate report for {package.username}: {e}"
            ) from e
