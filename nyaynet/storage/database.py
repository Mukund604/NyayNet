"""SQLite database connection and schema initialization."""

import sqlite3
from pathlib import Path

from config.logging_config import get_logger

log = get_logger(__name__)

SCHEMA_SQL = """
-- Comments table (immutable, INSERT only)
CREATE TABLE IF NOT EXISTS comments (
    id TEXT PRIMARY KEY,
    instagram_comment_id TEXT UNIQUE,
    instagram_post_id TEXT,
    username TEXT NOT NULL,
    text TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    source TEXT NOT NULL,
    raw_data TEXT,
    checksum TEXT NOT NULL,
    ingested_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_comments_username ON comments(username);
CREATE INDEX IF NOT EXISTS idx_comments_timestamp ON comments(timestamp);
CREATE INDEX IF NOT EXISTS idx_comments_instagram_id ON comments(instagram_comment_id);

-- Classification results
CREATE TABLE IF NOT EXISTS classification_results (
    id TEXT PRIMARY KEY,
    comment_id TEXT NOT NULL REFERENCES comments(id),
    method TEXT NOT NULL,  -- 'local', 'llm', 'hybrid'
    labels TEXT NOT NULL,  -- JSON array of labels
    confidence_scores TEXT NOT NULL,  -- JSON dict of label -> score
    overall_confidence REAL NOT NULL,
    is_hateful INTEGER NOT NULL DEFAULT 0,
    reasoning TEXT,
    model_name TEXT,
    classified_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_classification_comment ON classification_results(comment_id);
CREATE INDEX IF NOT EXISTS idx_classification_confidence ON classification_results(overall_confidence);

-- Severity scores
CREATE TABLE IF NOT EXISTS severity_scores (
    id TEXT PRIMARY KEY,
    comment_id TEXT NOT NULL REFERENCES comments(id),
    classification_id TEXT NOT NULL REFERENCES classification_results(id),
    raw_score REAL NOT NULL,
    normalized_score REAL NOT NULL,
    severity_level TEXT NOT NULL,
    weight_breakdown TEXT NOT NULL,  -- JSON dict
    scored_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_severity_comment ON severity_scores(comment_id);

-- User behavior profiles
CREATE TABLE IF NOT EXISTS user_behavior_profiles (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    total_comments INTEGER NOT NULL DEFAULT 0,
    offensive_comments INTEGER NOT NULL DEFAULT 0,
    offense_rate REAL NOT NULL DEFAULT 0.0,
    repeat_offender_score REAL NOT NULL DEFAULT 0.0,
    escalation_trend REAL NOT NULL DEFAULT 0.0,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    label_distribution TEXT NOT NULL DEFAULT '{}',  -- JSON dict
    severity_history TEXT NOT NULL DEFAULT '[]',  -- JSON array
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_behavior_username ON user_behavior_profiles(username);
CREATE INDEX IF NOT EXISTS idx_behavior_offender_score ON user_behavior_profiles(repeat_offender_score);

-- Decisions
CREATE TABLE IF NOT EXISTS decisions (
    id TEXT PRIMARY KEY,
    comment_id TEXT NOT NULL REFERENCES comments(id),
    username TEXT NOT NULL,
    action TEXT NOT NULL,
    confidence REAL NOT NULL,
    severity_level TEXT,
    reasoning TEXT NOT NULL,
    rule_triggers TEXT NOT NULL DEFAULT '[]',  -- JSON array
    cooldown_until TEXT,
    requires_human_approval INTEGER NOT NULL DEFAULT 1,
    human_approved INTEGER,
    approved_by TEXT,
    approved_at TEXT,
    decided_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_decisions_comment ON decisions(comment_id);
CREATE INDEX IF NOT EXISTS idx_decisions_username ON decisions(username);
CREATE INDEX IF NOT EXISTS idx_decisions_action ON decisions(action);

-- Evidence packages
CREATE TABLE IF NOT EXISTS evidence_packages (
    id TEXT PRIMARY KEY,
    decision_id TEXT NOT NULL REFERENCES decisions(id),
    username TEXT NOT NULL,
    comment_ids TEXT NOT NULL,  -- JSON array
    screenshots TEXT NOT NULL DEFAULT '[]',  -- JSON array of file paths
    report_path TEXT,
    complaint_text TEXT,
    legal_sections TEXT NOT NULL DEFAULT '[]',  -- JSON array
    metadata TEXT NOT NULL DEFAULT '{}',  -- JSON dict
    compiled_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_evidence_decision ON evidence_packages(decision_id);

-- Complaints
CREATE TABLE IF NOT EXISTS complaints (
    id TEXT PRIMARY KEY,
    evidence_package_id TEXT NOT NULL REFERENCES evidence_packages(id),
    portal_complaint_id TEXT,
    status TEXT NOT NULL,
    submission_data TEXT,  -- JSON dict (sanitized)
    portal_response TEXT,
    confirmation_screenshot TEXT,
    filed_at TEXT,
    last_checked TEXT,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_complaints_status ON complaints(status);
CREATE INDEX IF NOT EXISTS idx_complaints_evidence ON complaints(evidence_package_id);

-- Audit log (hash-chained)
CREATE TABLE IF NOT EXISTS audit_log (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    actor TEXT NOT NULL DEFAULT 'system',
    details TEXT NOT NULL DEFAULT '{}',  -- JSON
    previous_hash TEXT NOT NULL,
    entry_hash TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_log(entity_type, entity_id);
"""


def get_connection(db_path: str) -> sqlite3.Connection:
    """Create a database connection with proper settings."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row

    # Enable WAL mode and foreign keys
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")

    return conn


def init_database(db_path: str) -> sqlite3.Connection:
    """Initialize the database with the full schema."""
    conn = get_connection(db_path)
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    log.info("database_initialized", path=db_path)
    return conn
