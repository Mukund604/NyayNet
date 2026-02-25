"""Enums and constants used across NyayNet."""

from enum import Enum


class DetectionLabel(str, Enum):
    """Classification labels for comment detection."""
    NORMAL = "normal"
    ABUSE = "abuse"
    SEXUAL = "sexual"
    THREAT = "threat"
    DOXXING = "doxxing"
    HATE_SPEECH = "hate_speech"


class SeverityLevel(str, Enum):
    """Severity levels for scored comments."""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class DecisionAction(str, Enum):
    """Actions the system can take."""
    IGNORE = "ignore"
    FLAG = "flag"
    WARN = "warn"
    RECOMMEND_COMPLAINT = "recommend_complaint"
    AUTO_FILE_COMPLAINT = "auto_file_complaint"


class ComplaintStatus(str, Enum):
    """Status of a filed complaint."""
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    FILING_IN_PROGRESS = "filing_in_progress"
    FILED = "filed"
    FILING_FAILED = "filing_failed"
    ACKNOWLEDGED = "acknowledged"
    UNDER_INVESTIGATION = "under_investigation"
    RESOLVED = "resolved"
    REJECTED = "rejected"


class IngestionSource(str, Enum):
    """Source of ingested comments."""
    INSTAGRAM_API = "instagram_api"
    MOCK = "mock"
    MANUAL = "manual"


# Severity weights for different harassment categories
SEVERITY_WEIGHTS = {
    DetectionLabel.SEXUAL: 5,
    DetectionLabel.THREAT: 7,
    DetectionLabel.ABUSE: 3,
    DetectionLabel.DOXXING: 6,
    DetectionLabel.HATE_SPEECH: 4,
    DetectionLabel.NORMAL: 0,
}

# Severity level thresholds (on normalized 0-1 scale)
SEVERITY_THRESHOLDS = {
    SeverityLevel.LOW: 0.2,
    SeverityLevel.MODERATE: 0.5,
    SeverityLevel.HIGH: 0.75,
    SeverityLevel.CRITICAL: 0.9,
}

# Portal form selectors (configurable for UI resilience)
PORTAL_SELECTORS = {
    "category_dropdown": "#categoryId",
    "subcategory_dropdown": "#subCategoryId",
    "description_textarea": "#description",
    "incident_date": "#incidentDate",
    "submit_button": "#submitBtn",
    "otp_input": "#otpInput",
    "otp_submit": "#otpSubmitBtn",
    "captcha_image": "#captchaImage",
    "captcha_input": "#captchaInput",
    "file_upload": "#fileUpload",
    "complaint_id_display": "#complaintId",
    "name_input": "#complainantName",
    "email_input": "#complainantEmail",
    "phone_input": "#complainantPhone",
    "state_dropdown": "#stateId",
    "city_input": "#cityDistrict",
}

# Cyber crime portal category mappings
PORTAL_CATEGORIES = {
    "online_harassment": "Women/Child Related Crime",
    "cyber_bullying": "Women/Child Related Crime",
    "hate_speech": "Other Cyber Crime",
    "threat": "Other Cyber Crime",
    "doxxing": "Other Cyber Crime",
}

PORTAL_SUBCATEGORIES = {
    "online_harassment": "Cyber Bullying/Stalking/Sexting",
    "cyber_bullying": "Cyber Bullying/Stalking/Sexting",
    "hate_speech": "Cyber Terrorism",
    "threat": "Cyber Terrorism",
    "doxxing": "Online Threat",
}
