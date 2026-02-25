"""Claude API integration for borderline multi-label classification."""

import json

import anthropic

from config.constants import DetectionLabel
from config.logging_config import get_logger
from nyaynet.common.exceptions import LLMError
from nyaynet.detection.models import ClassificationResult

log = get_logger(__name__)

CLASSIFICATION_PROMPT = """You are a content moderation expert specializing in online harassment detection for Indian social media. Analyze the following comment and classify it.

Comment: "{text}"
Context: This comment was posted on Instagram.{lang_context}

Classify this comment into the following categories with probability scores (0.0 to 1.0):
1. **normal** - Not harassment, regular conversation
2. **abuse** - General verbal abuse, insults, bullying
3. **sexual** - Sexual harassment, unsolicited sexual content, objectification
4. **threat** - Threats of violence, harm, or intimidation
5. **doxxing** - Sharing/threatening to share personal information
6. **hate_speech** - Hate speech targeting identity (caste, religion, gender, ethnicity)

Respond ONLY with a JSON object in this exact format:
{{
    "labels": ["primary_label", "secondary_label"],
    "scores": {{
        "normal": 0.0,
        "abuse": 0.0,
        "sexual": 0.0,
        "threat": 0.0,
        "doxxing": 0.0,
        "hate_speech": 0.0
    }},
    "is_hateful": true,
    "reasoning": "Brief explanation of classification"
}}

Rules:
- "labels" should list ALL applicable labels where score > 0.3, most severe first
- Scores must sum to approximately 1.0
- Consider Indian languages (Hindi, Hinglish), cultural context, and slang
- For ambiguous cases, lean toward flagging (better safe than sorry)
- "is_hateful" is true if any non-normal label has score > 0.5"""


class LLMClassifier:
    """Claude API-based classifier for precise multi-label classification."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-5-20250929", max_tokens: int = 1024):
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    def classify(self, comment_id: str, text: str, language: str = "en") -> ClassificationResult:
        """Classify a comment using Claude API."""
        lang_context = ""
        if language != "en":
            lang_context = f"\nOriginal language detected: {language}. The text may contain Hindi, Hinglish (Hindi-English mix), or other Indian languages."

        prompt = CLASSIFICATION_PROMPT.format(text=text, lang_context=lang_context)

        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = response.content[0].text.strip()
            return self._parse_response(comment_id, response_text)

        except anthropic.APIError as e:
            raise LLMError(f"Claude API error: {e}") from e
        except Exception as e:
            raise LLMError(f"LLM classification failed: {e}") from e

    def _parse_response(self, comment_id: str, response_text: str) -> ClassificationResult:
        """Parse Claude's JSON response into a ClassificationResult."""
        try:
            # Extract JSON from response (handle markdown code blocks)
            json_text = response_text
            if "```" in json_text:
                json_text = json_text.split("```")[1]
                if json_text.startswith("json"):
                    json_text = json_text[4:]
                json_text = json_text.strip()

            data = json.loads(json_text)

            # Map string labels to DetectionLabel enums
            label_map = {
                "normal": DetectionLabel.NORMAL,
                "abuse": DetectionLabel.ABUSE,
                "sexual": DetectionLabel.SEXUAL,
                "threat": DetectionLabel.THREAT,
                "doxxing": DetectionLabel.DOXXING,
                "hate_speech": DetectionLabel.HATE_SPEECH,
            }

            labels = []
            for label_str in data.get("labels", []):
                if label_str in label_map:
                    labels.append(label_map[label_str])

            if not labels:
                labels = [DetectionLabel.NORMAL]

            scores = data.get("scores", {})
            is_hateful = data.get("is_hateful", False)

            # Overall confidence = max score
            overall_confidence = max(scores.values()) if scores else 0.5

            return ClassificationResult(
                comment_id=comment_id,
                method="llm",
                labels=labels,
                confidence_scores=scores,
                overall_confidence=overall_confidence,
                is_hateful=is_hateful,
                reasoning=data.get("reasoning"),
                model_name=self._model,
            )

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            log.error("llm_response_parse_failed", error=str(e), response=response_text)
            # Fallback: flag as needing review
            return ClassificationResult(
                comment_id=comment_id,
                method="llm",
                labels=[DetectionLabel.ABUSE],
                confidence_scores={"parse_error": 1.0},
                overall_confidence=0.5,
                is_hateful=True,
                reasoning=f"LLM response parsing failed: {e}. Flagged for safety.",
                model_name=self._model,
            )
