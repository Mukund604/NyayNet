"""Application settings using pydantic-settings."""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for NyayNet."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Claude API
    anthropic_api_key: str = ""

    # Instagram Graph API
    instagram_access_token: str = ""
    instagram_business_account_id: str = ""

    # Cyber Crime Portal - Complainant details
    portal_complainant_name: str = ""
    portal_complainant_email: str = ""
    portal_complainant_phone: str = ""
    portal_complainant_state: str = ""
    portal_complainant_city: str = ""

    # Encryption
    encryption_key: str = ""

    # Database
    database_path: str = "data/nyaynet.db"

    # Detection thresholds
    local_model_hate_threshold_high: float = 0.85
    local_model_hate_threshold_low: float = 0.4
    decision_confidence_threshold: float = 0.85
    min_offensive_comments: int = 3
    cooldown_hours: int = 24

    # Local model
    local_model_name: str = "Hate-speech-CNERG/dehatebert-mono-english"

    # Claude model
    claude_model: str = "claude-sonnet-4-5-20250929"
    claude_max_tokens: int = 1024

    # Notifications
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    notification_email: str = ""

    # Feature flags
    require_human_approval: bool = True
    use_mock_client: bool = True

    # Rate limiting
    api_rate_limit_per_minute: int = 30
    portal_rate_limit_per_hour: int = 5

    # Paths
    evidence_dir: str = "data/evidence"
    logs_dir: str = "data/logs"
    models_dir: str = "data/models"

    @property
    def database_full_path(self) -> Path:
        return Path(self.database_path)

    @property
    def evidence_full_path(self) -> Path:
        return Path(self.evidence_dir)

    @property
    def logs_full_path(self) -> Path:
        return Path(self.logs_dir)


def get_settings() -> Settings:
    """Get application settings singleton."""
    return Settings()
