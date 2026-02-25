"""Custom exception hierarchy for NyayNet."""


class NyayNetError(Exception):
    """Base exception for all NyayNet errors."""


# Ingestion errors
class IngestionError(NyayNetError):
    """Error during comment ingestion."""


class InstagramAPIError(IngestionError):
    """Error communicating with Instagram API."""


class RateLimitExceeded(InstagramAPIError):
    """Instagram API rate limit exceeded."""


# Detection errors
class DetectionError(NyayNetError):
    """Error during harassment detection."""


class ModelLoadError(DetectionError):
    """Error loading ML model."""


class ClassificationError(DetectionError):
    """Error during classification."""


class LLMError(DetectionError):
    """Error communicating with Claude API."""


# Storage errors
class StorageError(NyayNetError):
    """Error in storage layer."""


class DatabaseError(StorageError):
    """Database operation failed."""


class EncryptionError(StorageError):
    """Encryption/decryption failed."""


# Evidence errors
class EvidenceError(NyayNetError):
    """Error during evidence compilation."""


class ScreenshotError(EvidenceError):
    """Error capturing screenshot."""


class ReportGenerationError(EvidenceError):
    """Error generating PDF report."""


# Filing errors
class FilingError(NyayNetError):
    """Error during complaint filing."""


class PortalNavigationError(FilingError):
    """Error navigating the cyber crime portal."""


class OTPError(FilingError):
    """Error handling OTP verification."""


class CaptchaError(FilingError):
    """Error handling CAPTCHA."""


class FormSubmissionError(FilingError):
    """Error submitting the complaint form."""


# Decision errors
class DecisionError(NyayNetError):
    """Error in decision engine."""


class CooldownActiveError(DecisionError):
    """Action blocked due to cooldown period."""


# Audit errors
class AuditIntegrityError(NyayNetError):
    """Audit log integrity check failed."""
