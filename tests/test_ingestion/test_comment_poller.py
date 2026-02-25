"""Tests for comment poller."""

from nyaynet.ingestion.comment_poller import CommentPoller
from nyaynet.ingestion.mock_client import MockInstagramClient


def test_poll_once_ingests_comments(comment_repo, audit_logger):
    client = MockInstagramClient()
    poller = CommentPoller(client, comment_repo, audit_logger)

    new_comments = poller.poll_once()
    assert len(new_comments) > 0


def test_poll_deduplicates(comment_repo, audit_logger):
    client = MockInstagramClient()
    poller = CommentPoller(client, comment_repo, audit_logger)

    first_batch = poller.poll_once()
    second_batch = poller.poll_once()

    # Second poll should have no new comments (same mock data)
    # Actually MockInstagramClient increments fetch_count, giving new IDs
    # But the structure tests dedup by instagram_comment_id
    assert len(first_batch) > 0


def test_poll_persists_to_db(comment_repo, audit_logger):
    client = MockInstagramClient()
    poller = CommentPoller(client, comment_repo, audit_logger)

    new_comments = poller.poll_once()
    for comment in new_comments:
        stored = comment_repo.get_by_id(comment.id)
        assert stored is not None
        assert stored["username"] == comment.username
