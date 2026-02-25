"""Immutable hash-chained audit trail."""

import json
from typing import Any

from config.logging_config import get_logger
from nyaynet.common.utils import compute_chain_hash, generate_id, utc_now_iso

log = get_logger(__name__)

# Genesis hash for the first entry in the chain
GENESIS_HASH = "0" * 64


class AuditLogger:
    """Hash-chained audit logger that writes to the database."""

    def __init__(self, db):
        self._db = db
        self._last_hash = self._get_last_hash()

    def _get_last_hash(self) -> str:
        """Get the hash of the most recent audit entry."""
        cursor = self._db.execute(
            "SELECT entry_hash FROM audit_log ORDER BY rowid DESC LIMIT 1"
        )
        row = cursor.fetchone()
        return row["entry_hash"] if row else GENESIS_HASH

    def log(
        self,
        action: str,
        entity_type: str,
        entity_id: str,
        details: dict[str, Any] | None = None,
        actor: str = "system",
    ) -> str:
        """Record an audit event with hash chaining.

        Returns the entry ID.
        """
        entry_id = generate_id()
        timestamp = utc_now_iso()
        details_json = json.dumps(details or {}, sort_keys=True)

        # Build the data string for hashing
        data = f"{entry_id}|{timestamp}|{action}|{entity_type}|{entity_id}|{actor}|{details_json}"
        entry_hash = compute_chain_hash(data, self._last_hash)

        self._db.execute(
            """
            INSERT INTO audit_log (id, timestamp, action, entity_type, entity_id,
                                   actor, details, previous_hash, entry_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry_id,
                timestamp,
                action,
                entity_type,
                entity_id,
                actor,
                details_json,
                self._last_hash,
                entry_hash,
            ),
        )
        self._db.commit()
        self._last_hash = entry_hash

        log.info(
            "audit_entry",
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
        )
        return entry_id

    def verify_chain(self) -> bool:
        """Verify the integrity of the entire audit chain."""
        cursor = self._db.execute(
            "SELECT * FROM audit_log ORDER BY rowid ASC"
        )
        previous_hash = GENESIS_HASH

        for row in cursor:
            details_json = row["details"]
            data = (
                f"{row['id']}|{row['timestamp']}|{row['action']}|"
                f"{row['entity_type']}|{row['entity_id']}|{row['actor']}|{details_json}"
            )
            expected_hash = compute_chain_hash(data, previous_hash)

            if row["previous_hash"] != previous_hash:
                log.error("audit_chain_broken", entry_id=row["id"], field="previous_hash")
                return False
            if row["entry_hash"] != expected_hash:
                log.error("audit_chain_broken", entry_id=row["id"], field="entry_hash")
                return False

            previous_hash = row["entry_hash"]

        return True
