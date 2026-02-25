"""Hybrid detection engine: local screening -> confidence check -> LLM escalation."""

from config.logging_config import get_logger
from config.settings import Settings
from nyaynet.common.audit_logger import AuditLogger
from nyaynet.detection.llm_classifier import LLMClassifier
from nyaynet.detection.local_classifier import LocalClassifier
from nyaynet.detection.models import ClassificationResult
from nyaynet.detection.text_preprocessor import TextPreprocessor
from nyaynet.storage.repositories import ClassificationRepository

log = get_logger(__name__)


class HybridDetectionEngine:
    """Orchestrates local -> confidence check -> LLM escalation -> result merge."""

    def __init__(
        self,
        settings: Settings,
        local_classifier: LocalClassifier,
        llm_classifier: LLMClassifier | None,
        preprocessor: TextPreprocessor,
        classification_repo: ClassificationRepository,
        audit_logger: AuditLogger,
    ):
        self._settings = settings
        self._local = local_classifier
        self._llm = llm_classifier
        self._preprocessor = preprocessor
        self._repo = classification_repo
        self._audit = audit_logger

        self._threshold_high = settings.local_model_hate_threshold_high
        self._threshold_low = settings.local_model_hate_threshold_low

    def classify(self, comment_id: str, text: str) -> ClassificationResult:
        """Run the hybrid classification pipeline.

        Strategy:
        1. Preprocess text (language detection, transliteration, emoji decode, slang normalization)
        2. Run local model for binary hate/non-hate screening
        3. If high confidence non-hate (< threshold_low) -> NORMAL, skip LLM
        4. If high confidence hate (> threshold_high) -> flag with keyword-based labels
        5. If borderline (between thresholds) -> escalate to LLM for precise multi-label
        """
        # Step 1: Preprocess
        processed = self._preprocessor.preprocess(text)
        clean_text = processed["cleaned"]
        language = processed["language"]

        log.info(
            "classifying_comment",
            comment_id=comment_id,
            language=language,
            text_length=len(text),
        )

        # Step 2: Local model screening
        hate_prob = self._local.get_hate_probability(clean_text)

        # Step 3: High confidence non-hate
        if hate_prob < self._threshold_low:
            result = self._local.classify(comment_id, clean_text)
            result.method = "hybrid"
            log.info(
                "classified_as_normal",
                comment_id=comment_id,
                hate_prob=hate_prob,
            )

        # Step 4: High confidence hate
        elif hate_prob > self._threshold_high:
            result = self._local.classify(comment_id, clean_text)
            result.method = "hybrid"
            log.info(
                "classified_as_hateful_high_confidence",
                comment_id=comment_id,
                hate_prob=hate_prob,
            )

        # Step 5: Borderline -> escalate to LLM
        else:
            if self._llm:
                log.info(
                    "escalating_to_llm",
                    comment_id=comment_id,
                    hate_prob=hate_prob,
                )
                result = self._llm.classify(comment_id, text, language)
                result.method = "hybrid"
            else:
                # No LLM available, fall back to local
                log.warning(
                    "no_llm_available_using_local",
                    comment_id=comment_id,
                    hate_prob=hate_prob,
                )
                result = self._local.classify(comment_id, clean_text)
                result.method = "hybrid"

        # Persist result
        self._repo.insert(result.to_db_dict())

        # Audit
        self._audit.log(
            action="comment_classified",
            entity_type="classification",
            entity_id=result.id,
            details={
                "comment_id": comment_id,
                "method": result.method,
                "is_hateful": result.is_hateful,
                "labels": [l.value for l in result.labels],
                "overall_confidence": result.overall_confidence,
                "hate_prob": hate_prob,
            },
        )

        return result
