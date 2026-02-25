"""Pydantic models for the ingestion module."""

from pydantic import BaseModel, Field

from config.constants import IngestionSource
from nyaynet.common.utils import compute_sha256, generate_id, utc_now_iso


class IngestedComment(BaseModel):
    """Represents a comment ingested from any source."""

    id: str = Field(default_factory=generate_id)
    instagram_comment_id: str | None = None
    instagram_post_id: str | None = None
    username: str
    text: str
    timestamp: str = Field(default_factory=utc_now_iso)
    source: IngestionSource = IngestionSource.MOCK
    raw_data: dict = Field(default_factory=dict)
    checksum: str = ""
    ingested_at: str = Field(default_factory=utc_now_iso)

    def model_post_init(self, __context) -> None:
        if not self.checksum:
            self.checksum = compute_sha256(
                f"{self.username}|{self.text}|{self.timestamp}"
            )

    def to_db_dict(self) -> dict:
        """Convert to a dict suitable for database insertion."""
        return self.model_dump()
