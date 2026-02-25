"""Shared test fixtures for NyayNet."""

import json
import os
import sqlite3
import tempfile
from pathlib import Path

import pytest

# Set test environment before importing settings
os.environ.setdefault("DATABASE_PATH", ":memory:")
os.environ.setdefault("USE_MOCK_CLIENT", "true")
os.environ.setdefault("REQUIRE_HUMAN_APPROVAL", "true")

from config.settings import Settings
from nyaynet.common.audit_logger import AuditLogger
from nyaynet.storage.database import SCHEMA_SQL
from nyaynet.storage.repositories import (
    BehaviorRepository,
    ClassificationRepository,
    CommentRepository,
    ComplaintRepository,
    DecisionRepository,
    EvidenceRepository,
    SeverityRepository,
)


@pytest.fixture
def test_db():
    """Create an in-memory SQLite database with schema."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def settings():
    """Test settings with mock configuration."""
    return Settings(
        database_path=":memory:",
        use_mock_client=True,
        require_human_approval=True,
        anthropic_api_key="test-key",
        encryption_key="",
        evidence_dir=tempfile.mkdtemp(),
    )


@pytest.fixture
def comment_repo(test_db):
    return CommentRepository(test_db)


@pytest.fixture
def classification_repo(test_db):
    return ClassificationRepository(test_db)


@pytest.fixture
def severity_repo(test_db):
    return SeverityRepository(test_db)


@pytest.fixture
def behavior_repo(test_db):
    return BehaviorRepository(test_db)


@pytest.fixture
def decision_repo(test_db):
    return DecisionRepository(test_db)


@pytest.fixture
def evidence_repo(test_db):
    return EvidenceRepository(test_db)


@pytest.fixture
def complaint_repo(test_db):
    return ComplaintRepository(test_db)


@pytest.fixture
def audit_logger(test_db):
    return AuditLogger(test_db)


@pytest.fixture
def mock_comments():
    """Load mock comments from fixtures."""
    fixture_path = Path(__file__).parent / "fixtures" / "mock_comments.json"
    with open(fixture_path) as f:
        return json.load(f)


@pytest.fixture
def sample_comment_dict():
    """A single sample comment dict for insertion."""
    from nyaynet.common.utils import compute_sha256, generate_id, utc_now_iso

    text = "This is a test comment"
    username = "test_user"
    timestamp = utc_now_iso()
    return {
        "id": generate_id(),
        "instagram_comment_id": "ig_test_001",
        "instagram_post_id": "post_test_001",
        "username": username,
        "text": text,
        "timestamp": timestamp,
        "source": "mock",
        "raw_data": {},
        "checksum": compute_sha256(f"{username}|{text}|{timestamp}"),
    }


@pytest.fixture
def temp_dir():
    """Temporary directory for file operations."""
    with tempfile.TemporaryDirectory() as d:
        yield d
