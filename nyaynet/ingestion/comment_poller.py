"""Polling scheduler, deduplication, and persistence for comment ingestion."""

from config.logging_config import get_logger
from nyaynet.common.audit_logger import AuditLogger
from nyaynet.ingestion.instagram_client import InstagramClientBase
from nyaynet.ingestion.models import IngestedComment
from nyaynet.storage.repositories import CommentRepository

log = get_logger(__name__)


class CommentPoller:
    """Polls for new comments, deduplicates, and persists them."""

    def __init__(
        self,
        client: InstagramClientBase,
        comment_repo: CommentRepository,
        audit_logger: AuditLogger,
    ):
        self._client = client
        self._repo = comment_repo
        self._audit = audit_logger

    def poll_once(self, post_id: str | None = None, limit: int = 50) -> list[IngestedComment]:
        """Fetch comments, deduplicate, and persist new ones.

        Returns the list of newly ingested comments.
        """
        raw_comments = self._client.fetch_comments(post_id=post_id, limit=limit)
        new_comments = []

        for comment in raw_comments:
            # Dedup: skip if we've already seen this Instagram comment ID
            if comment.instagram_comment_id and self._repo.exists(
                comment.instagram_comment_id
            ):
                continue

            # Persist
            self._repo.insert(comment.to_db_dict())
            new_comments.append(comment)

            self._audit.log(
                action="comment_ingested",
                entity_type="comment",
                entity_id=comment.id,
                details={
                    "username": comment.username,
                    "source": comment.source.value,
                    "text_length": len(comment.text),
                },
            )

        log.info(
            "poll_complete",
            total_fetched=len(raw_comments),
            new_comments=len(new_comments),
            duplicates=len(raw_comments) - len(new_comments),
        )
        return new_comments
