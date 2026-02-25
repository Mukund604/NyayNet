"""HuggingFace dehatebert local classifier for binary hate/non-hate screening."""

import re

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from config.constants import DetectionLabel
from config.logging_config import get_logger
from nyaynet.common.exceptions import ClassificationError, ModelLoadError
from nyaynet.detection.models import ClassificationResult

log = get_logger(__name__)

# Keyword patterns for rough multi-label classification when local model flags hate
LABEL_PATTERNS = {
    DetectionLabel.SEXUAL: re.compile(
        r"\b(nude|nudes|sex|rape|molest|send pics|hot body|send nudes|sexual|"
        r"boobs|dick|pussy|f[*]ck|fck)\b",
        re.IGNORECASE,
    ),
    DetectionLabel.THREAT: re.compile(
        r"\b(kill|die|murder|attack|find you|find where you live|make you pay|"
        r"hurt you|beat you|destroy|bomb|gun|weapon|stab)\b",
        re.IGNORECASE,
    ),
    DetectionLabel.DOXXING: re.compile(
        r"\b(address|phone number|where you live|dox|doxx|leak your|"
        r"found your|know your school|your house|your home|personal info)\b",
        re.IGNORECASE,
    ),
    DetectionLabel.HATE_SPEECH: re.compile(
        r"\b(don.t belong|go back|your kind|your people|community|"
        r"disease|vermin|subhuman|inferior|don.t deserve)\b",
        re.IGNORECASE,
    ),
    DetectionLabel.ABUSE: re.compile(
        r"\b(stupid|idiot|moron|trash|garbage|worthless|pathetic|loser|"
        r"ugly|disgusting|shut up|delete your|abusive_slang)\b",
        re.IGNORECASE,
    ),
}


class LocalClassifier:
    """Binary hate/non-hate classifier using dehatebert."""

    def __init__(self, model_name: str = "Hate-speech-CNERG/dehatebert-mono-english"):
        self._model_name = model_name
        self._model = None
        self._tokenizer = None
        self._device = "cpu"

    def load(self) -> None:
        """Load the model and tokenizer."""
        try:
            log.info("loading_local_model", model=self._model_name)
            self._tokenizer = AutoTokenizer.from_pretrained(self._model_name)
            self._model = AutoModelForSequenceClassification.from_pretrained(
                self._model_name
            )
            if torch.backends.mps.is_available():
                self._device = "mps"
            elif torch.cuda.is_available():
                self._device = "cuda"
            self._model.to(self._device)
            self._model.eval()
            log.info("local_model_loaded", device=self._device)
        except Exception as e:
            raise ModelLoadError(f"Failed to load model {self._model_name}: {e}") from e

    def _ensure_loaded(self) -> None:
        if self._model is None:
            self.load()

    def classify(self, comment_id: str, text: str) -> ClassificationResult:
        """Classify text as hate/non-hate with a confidence score."""
        self._ensure_loaded()

        try:
            inputs = self._tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True,
            ).to(self._device)

            with torch.no_grad():
                outputs = self._model(**inputs)
                probs = torch.softmax(outputs.logits, dim=-1)

            # dehatebert: index 0 = NON_HATE, index 1 = HATE
            hate_prob = probs[0][1].item()
            non_hate_prob = probs[0][0].item()

            is_hateful = hate_prob > 0.5
            labels = []
            confidence_scores = {"hate": hate_prob, "non_hate": non_hate_prob}

            if is_hateful:
                # Use keyword matching for rough multi-label
                labels = self._get_keyword_labels(text)
                if not labels:
                    labels = [DetectionLabel.ABUSE]  # Default to abuse
            else:
                labels = [DetectionLabel.NORMAL]

            return ClassificationResult(
                comment_id=comment_id,
                method="local",
                labels=labels,
                confidence_scores=confidence_scores,
                overall_confidence=max(hate_prob, non_hate_prob),
                is_hateful=is_hateful,
                model_name=self._model_name,
            )
        except Exception as e:
            raise ClassificationError(f"Classification failed: {e}") from e

    def get_hate_probability(self, text: str) -> float:
        """Get the hate probability for a text. Used by hybrid engine for threshold checks."""
        self._ensure_loaded()

        inputs = self._tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True,
        ).to(self._device)

        with torch.no_grad():
            outputs = self._model(**inputs)
            probs = torch.softmax(outputs.logits, dim=-1)

        return probs[0][1].item()

    def _get_keyword_labels(self, text: str) -> list[DetectionLabel]:
        """Use keyword patterns to determine multi-label classification."""
        labels = []
        for label, pattern in LABEL_PATTERNS.items():
            if pattern.search(text):
                labels.append(label)
        return labels
