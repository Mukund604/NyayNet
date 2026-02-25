"""Tests for database initialization and schema."""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from nyaynet.storage.database import get_connection, init_database


def test_init_database_creates_file():
    with tempfile.TemporaryDirectory() as d:
        db_path = str(Path(d) / "test.db")
        conn = init_database(db_path)
        assert Path(db_path).exists()
        conn.close()


def test_init_database_creates_tables():
    with tempfile.TemporaryDirectory() as d:
        db_path = str(Path(d) / "test.db")
        conn = init_database(db_path)

        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row["name"] for row in cursor.fetchall()]

        expected = [
            "audit_log",
            "classification_results",
            "comments",
            "complaints",
            "decisions",
            "evidence_packages",
            "severity_scores",
            "user_behavior_profiles",
        ]
        for table in expected:
            assert table in tables, f"Missing table: {table}"

        conn.close()


def test_wal_mode_enabled():
    with tempfile.TemporaryDirectory() as d:
        db_path = str(Path(d) / "test.db")
        conn = init_database(db_path)
        cursor = conn.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]
        assert mode == "wal"
        conn.close()


def test_foreign_keys_enabled():
    with tempfile.TemporaryDirectory() as d:
        db_path = str(Path(d) / "test.db")
        conn = init_database(db_path)
        cursor = conn.execute("PRAGMA foreign_keys")
        fk = cursor.fetchone()[0]
        assert fk == 1
        conn.close()


def test_idempotent_init():
    """Calling init_database twice should not error."""
    with tempfile.TemporaryDirectory() as d:
        db_path = str(Path(d) / "test.db")
        conn1 = init_database(db_path)
        conn1.close()
        conn2 = init_database(db_path)
        conn2.close()
