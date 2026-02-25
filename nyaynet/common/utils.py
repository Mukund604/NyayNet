"""Shared utility functions."""

import hashlib
import uuid
from datetime import datetime, timezone


def generate_id() -> str:
    """Generate a unique ID."""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    """Get current UTC datetime as ISO string."""
    return utc_now().isoformat()


def compute_sha256(data: str) -> str:
    """Compute SHA-256 hash of a string."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def compute_chain_hash(data: str, previous_hash: str) -> str:
    """Compute a chain hash by combining data with the previous hash."""
    combined = f"{previous_hash}:{data}"
    return compute_sha256(combined)


def truncate_text(text: str, max_length: int = 500) -> str:
    """Truncate text to a maximum length, adding ellipsis if needed."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."
