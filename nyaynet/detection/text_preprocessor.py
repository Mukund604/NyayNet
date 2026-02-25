"""Text preprocessing: language detection, transliteration, emoji decode, slang normalization."""

import re

import emoji
from langdetect import detect, LangDetectException

from config.logging_config import get_logger

log = get_logger(__name__)

# Common Hinglish/Hindi abusive slang mappings to English equivalents
SLANG_NORMALIZATIONS = {
    "bc": "abusive_slang",
    "mc": "abusive_slang",
    "bsdk": "abusive_slang",
    "chutiya": "abusive_slang",
    "madarchod": "abusive_slang",
    "bhenchod": "abusive_slang",
    "gaandu": "abusive_slang",
    "randi": "abusive_slang",
    "saala": "abusive_slang",
    "saali": "abusive_slang",
    "kutta": "dog",
    "kutti": "dog",
    "harami": "abusive_slang",
    "kamina": "abusive_slang",
    "kameeni": "abusive_slang",
    # Common leet/creative spelling
    "k1ll": "kill",
    "d1e": "die",
    "r@pe": "rape",
    "h0e": "hoe",
    "b1tch": "bitch",
    "sh1t": "shit",
    "a$$": "ass",
    "fck": "fuck",
    "stfu": "shut up",
    "kys": "kill yourself",
}


class TextPreprocessor:
    """Preprocesses text for classification."""

    def preprocess(self, text: str) -> dict:
        """Full preprocessing pipeline.

        Returns a dict with:
            - original: original text
            - cleaned: cleaned text for classification
            - language: detected language
            - transliterated: transliterated text (if applicable)
            - emoji_decoded: text with emoji names
        """
        language = self.detect_language(text)
        emoji_decoded = self.decode_emojis(text)
        cleaned = self.clean_text(emoji_decoded)
        normalized = self.normalize_slang(cleaned)
        transliterated = self.transliterate(normalized, language)

        return {
            "original": text,
            "cleaned": transliterated,
            "language": language,
            "transliterated": transliterated,
            "emoji_decoded": emoji_decoded,
        }

    def detect_language(self, text: str) -> str:
        """Detect the language of the text."""
        # Remove emojis and URLs for better detection
        clean = re.sub(r"http\S+|www\S+", "", text)
        clean = emoji.replace_emoji(clean, replace="")
        clean = clean.strip()

        if not clean:
            return "en"

        try:
            lang = detect(clean)
            return lang
        except LangDetectException:
            return "en"

    def decode_emojis(self, text: str) -> str:
        """Replace emojis with their text descriptions."""
        return emoji.demojize(text, delimiters=(" [", "] "))

    def clean_text(self, text: str) -> str:
        """Clean text: remove URLs, normalize whitespace, lowercase."""
        # Remove URLs
        text = re.sub(r"http\S+|www\S+", "", text)
        # Remove @mentions (keep the text for context)
        text = re.sub(r"@(\w+)", r"\1", text)
        # Remove hashtag symbols but keep text
        text = re.sub(r"#(\w+)", r"\1", text)
        # Normalize whitespace
        text = re.sub(r"\s+", " ", text).strip()
        # Lowercase
        text = text.lower()
        return text

    def normalize_slang(self, text: str) -> str:
        """Normalize known slang and creative spellings."""
        words = text.split()
        normalized = []
        for word in words:
            lower_word = word.lower().strip(".,!?;:")
            if lower_word in SLANG_NORMALIZATIONS:
                normalized.append(SLANG_NORMALIZATIONS[lower_word])
            else:
                normalized.append(word)
        return " ".join(normalized)

    def transliterate(self, text: str, language: str) -> str:
        """Transliterate Hindi/Devanagari text to Roman script."""
        if language not in ("hi", "mr", "ne", "sa"):
            return text

        try:
            from indic_transliteration import sanscript
            from indic_transliteration.sanscript import transliterate as indic_trans

            return indic_trans(text, sanscript.DEVANAGARI, sanscript.IAST)
        except (ImportError, Exception) as e:
            log.warning("transliteration_failed", language=language, error=str(e))
            return text
