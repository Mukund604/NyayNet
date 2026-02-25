"""Tests for filing models."""

from config.constants import ComplaintStatus
from nyaynet.filing.models import ComplaintSubmission, FilingResult


def test_complaint_submission_creation():
    submission = ComplaintSubmission(
        complainant_name="Test User",
        complainant_email="test@example.com",
        complainant_phone="9876543210",
        complainant_state="Maharashtra",
        complainant_city="Mumbai",
        category="Women/Child Related Crime",
        subcategory="Cyber Bullying/Stalking/Sexting",
        description="Test complaint",
        incident_date="2024-01-15",
    )
    assert submission.complainant_name == "Test User"
    assert submission.evidence_files == []


def test_filing_result_defaults():
    result = FilingResult(evidence_package_id="ep_1")
    assert result.status == ComplaintStatus.PENDING_REVIEW
    assert result.portal_complaint_id is None
    assert result.id  # Auto-generated


def test_filing_result_to_db_dict():
    result = FilingResult(
        evidence_package_id="ep_1",
        status=ComplaintStatus.FILED,
        portal_complaint_id="CYB-2024-001",
    )
    db_dict = result.to_db_dict()
    assert db_dict["status"] == "filed"
    assert db_dict["portal_complaint_id"] == "CYB-2024-001"
