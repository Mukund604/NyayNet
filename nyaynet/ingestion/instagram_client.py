"""Abstract base and Graph API implementation for Instagram comment fetching."""

from abc import ABC, abstractmethod

import httpx

from config.logging_config import get_logger
from nyaynet.common.exceptions import InstagramAPIError, RateLimitExceeded
from nyaynet.ingestion.models import IngestedComment

log = get_logger(__name__)

GRAPH_API_BASE = "https://graph.facebook.com/v18.0"


class InstagramClientBase(ABC):
    """Abstract base class for Instagram comment fetching."""

    @abstractmethod
    def fetch_comments(self, post_id: str | None = None, limit: int = 50) -> list[IngestedComment]:
        """Fetch comments from Instagram."""


class InstagramGraphClient(InstagramClientBase):
    """Instagram Graph API implementation."""

    def __init__(self, access_token: str, business_account_id: str):
        self._access_token = access_token
        self._account_id = business_account_id
        self._client = httpx.Client(timeout=30.0)

    def _get_media_ids(self, limit: int = 25) -> list[str]:
        """Get recent media IDs for the business account."""
        url = f"{GRAPH_API_BASE}/{self._account_id}/media"
        params = {
            "access_token": self._access_token,
            "limit": limit,
            "fields": "id",
        }
        try:
            resp = self._client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            return [item["id"] for item in data.get("data", [])]
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise RateLimitExceeded("Instagram API rate limit exceeded") from e
            raise InstagramAPIError(f"Failed to fetch media: {e}") from e

    def fetch_comments(self, post_id: str | None = None, limit: int = 50) -> list[IngestedComment]:
        """Fetch comments from Instagram posts."""
        comments = []

        if post_id:
            media_ids = [post_id]
        else:
            media_ids = self._get_media_ids()

        for media_id in media_ids:
            url = f"{GRAPH_API_BASE}/{media_id}/comments"
            params = {
                "access_token": self._access_token,
                "limit": limit,
                "fields": "id,text,timestamp,username",
            }
            try:
                resp = self._client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()

                for item in data.get("data", []):
                    comment = IngestedComment(
                        instagram_comment_id=item["id"],
                        instagram_post_id=media_id,
                        username=item.get("username", "unknown"),
                        text=item.get("text", ""),
                        timestamp=item.get("timestamp", ""),
                        source="instagram_api",
                        raw_data=item,
                    )
                    comments.append(comment)

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    raise RateLimitExceeded("Instagram API rate limit exceeded") from e
                log.warning("fetch_comments_failed", media_id=media_id, error=str(e))

        log.info("comments_fetched", count=len(comments))
        return comments
