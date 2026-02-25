"""Tests for text preprocessor."""

from nyaynet.detection.text_preprocessor import TextPreprocessor


def test_preprocess_returns_dict():
    pp = TextPreprocessor()
    result = pp.preprocess("Hello world")
    assert "original" in result
    assert "cleaned" in result
    assert "language" in result


def test_clean_text_removes_urls():
    pp = TextPreprocessor()
    cleaned = pp.clean_text("Check out https://example.com for more")
    assert "https" not in cleaned
    assert "example.com" not in cleaned


def test_clean_text_normalizes_mentions():
    pp = TextPreprocessor()
    cleaned = pp.clean_text("Hey @user123 look at this")
    assert "@" not in cleaned
    assert "user123" in cleaned


def test_clean_text_normalizes_hashtags():
    pp = TextPreprocessor()
    cleaned = pp.clean_text("This is #awesome")
    assert "#" not in cleaned
    assert "awesome" in cleaned


def test_clean_text_lowercases():
    pp = TextPreprocessor()
    cleaned = pp.clean_text("THIS IS SHOUTING")
    assert cleaned == "this is shouting"


def test_decode_emojis():
    pp = TextPreprocessor()
    decoded = pp.decode_emojis("Hello 🔥 world")
    assert "fire" in decoded.lower()


def test_normalize_slang():
    pp = TextPreprocessor()
    assert "kill yourself" in pp.normalize_slang("kys")
    assert "bitch" in pp.normalize_slang("b1tch")
    assert "abusive_slang" in pp.normalize_slang("bc")


def test_detect_language_english():
    pp = TextPreprocessor()
    lang = pp.detect_language("This is a normal English sentence about photography.")
    assert lang == "en"


def test_detect_language_empty():
    pp = TextPreprocessor()
    lang = pp.detect_language("")
    assert lang == "en"  # Default


def test_preprocess_empty_text():
    pp = TextPreprocessor()
    result = pp.preprocess("")
    assert result["cleaned"] == ""


def test_preprocess_preserves_original():
    pp = TextPreprocessor()
    original = "Hello @world #test https://example.com 🔥"
    result = pp.preprocess(original)
    assert result["original"] == original
