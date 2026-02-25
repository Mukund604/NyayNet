"""Tests for mock Instagram client."""

from nyaynet.ingestion.mock_client import MockInstagramClient


def test_fetch_all_comments():
    client = MockInstagramClient()
    comments = client.fetch_comments()
    assert len(comments) > 0
    for comment in comments:
        assert comment.username
        assert comment.text is not None
        assert comment.source.value == "mock"


def test_fetch_by_post_id():
    client = MockInstagramClient()
    comments = client.fetch_comments(post_id="post_001")
    assert len(comments) > 0
    for comment in comments:
        assert comment.instagram_post_id == "post_001"


def test_fetch_with_limit():
    client = MockInstagramClient()
    comments = client.fetch_comments(limit=3)
    assert len(comments) <= 3


def test_unique_instagram_ids():
    client = MockInstagramClient()
    comments = client.fetch_comments()
    ids = [c.instagram_comment_id for c in comments]
    assert len(ids) == len(set(ids)), "Comment IDs should be unique"


def test_comments_have_checksums():
    client = MockInstagramClient()
    comments = client.fetch_comments()
    for comment in comments:
        assert comment.checksum
        assert len(comment.checksum) == 64  # SHA-256 hex digest
