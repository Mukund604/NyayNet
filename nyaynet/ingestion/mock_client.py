"""Mock client with canned data for development."""

from config.constants import IngestionSource
from config.logging_config import get_logger
from nyaynet.ingestion.instagram_client import InstagramClientBase
from nyaynet.ingestion.models import IngestedComment

log = get_logger(__name__)

# Realistic mock comments: English, Hindi, Hinglish, abusive, normal, borderline
MOCK_COMMENTS = [
    # Normal comments
    {"username": "travel_fan", "text": "Love this photo! Where was it taken?", "post_id": "post_001"},
    {"username": "foodie_99", "text": "The sunset looks amazing! Great capture.", "post_id": "post_001"},
    {"username": "art_lover", "text": "Beautiful composition, keep posting!", "post_id": "post_002"},
    {"username": "music_buff", "text": "This is so inspiring, thank you for sharing", "post_id": "post_002"},
    {"username": "reader_123", "text": "Bahut accha hai ye! (This is very good!)", "post_id": "post_003"},
    # Borderline comments
    {"username": "edge_case1", "text": "You think you're so smart? Everyone can see through your fake posts", "post_id": "post_001"},
    {"username": "edge_case2", "text": "This is the worst thing I've ever seen, just terrible content", "post_id": "post_002"},
    {"username": "troll_42", "text": "Lol nobody cares about your opinion, sit down", "post_id": "post_003"},
    # Abusive comments (English)
    {"username": "harasser_01", "text": "You're disgusting, go kill yourself nobody wants you here", "post_id": "post_001"},
    {"username": "harasser_01", "text": "I will find where you live and make you pay for this", "post_id": "post_002"},
    {"username": "harasser_01", "text": "You ugly piece of trash, delete your account", "post_id": "post_003"},
    {"username": "bully_55", "text": "Send me pics or I'll leak your photos everywhere", "post_id": "post_001"},
    {"username": "bully_55", "text": "I know your school, I'll tell everyone what you really are", "post_id": "post_002"},
    # Abusive comments (Hindi/Hinglish)
    {"username": "troll_hindi", "text": "Tu ja mar, tere jaisi ko koi nahi chahta", "post_id": "post_003"},
    {"username": "troll_hindi", "text": "Teri photos leak kar dunga, dekh lena", "post_id": "post_001"},
    {"username": "abuser_mix", "text": "You saali, tera number hai mere paas, ghar aa jaunga", "post_id": "post_002"},
    # Hate speech
    {"username": "hater_77", "text": "People like you don't deserve to exist, your community is a disease", "post_id": "post_001"},
    {"username": "hater_77", "text": "Go back to where you came from, you don't belong here", "post_id": "post_003"},
    # Doxxing attempt
    {"username": "doxxer_x", "text": "I found your address, it's in Andheri right? Everyone should know where this person lives", "post_id": "post_002"},
    # Sexual harassment
    {"username": "creep_99", "text": "You look so hot, send nudes or I'll find them myself", "post_id": "post_001"},
    {"username": "creep_99", "text": "I've been watching all your stories, I know your daily routine now", "post_id": "post_003"},
    # More normal for balance
    {"username": "positive_vibes", "text": "You're so talented, never stop creating!", "post_id": "post_001"},
    {"username": "supporter_1", "text": "Proud of you! Ignore the haters.", "post_id": "post_002"},
    {"username": "new_follower", "text": "Just found your page, love the aesthetic!", "post_id": "post_003"},
]


class MockInstagramClient(InstagramClientBase):
    """Mock client that returns canned comments for development."""

    def __init__(self):
        self._comments = MOCK_COMMENTS
        self._fetch_count = 0

    def fetch_comments(self, post_id: str | None = None, limit: int = 50) -> list[IngestedComment]:
        """Return mock comments, optionally filtered by post_id."""
        self._fetch_count += 1
        source_comments = self._comments

        if post_id:
            source_comments = [c for c in source_comments if c["post_id"] == post_id]

        results = []
        for i, c in enumerate(source_comments[:limit]):
            comment = IngestedComment(
                instagram_comment_id=f"mock_{self._fetch_count}_{i}",
                instagram_post_id=c["post_id"],
                username=c["username"],
                text=c["text"],
                source=IngestionSource.MOCK,
            )
            results.append(comment)

        log.info("mock_comments_fetched", count=len(results))
        return results
