from unittest.mock import patch

from src.pipeline import _detect_language


class TestLanguageDetector:
    def test_detect_english_text(self, sample_english_text):
        result = _detect_language(sample_english_text)
        assert result == "en"

    def test_detect_french_text(self, sample_french_text):
        result = _detect_language(sample_french_text)
        assert result == "fr"

    def test_detect_mixed_text_returns_dominant(self, mixed_english_heavy_text):
        result = _detect_language(mixed_english_heavy_text)
        assert result == "en"

    def test_detect_mixed_text_french_returns_dominant(self, mixed_french_heavy_text):
        result = _detect_language(mixed_french_heavy_text)
        assert result == "fr"

    def test_fallback_to_english_on_empty_text(self):
        result = _detect_language("")
        assert result == "en"

    def test_fallback_to_english_on_whitespace_only(self):
        result = _detect_language("   \n\t  ")
        assert result == "en"

    def test_fallback_to_english_on_exception(self):
        with patch("src.pipeline.langdetect.detect_langs", side_effect=Exception("error")):
            result = _detect_language("test text")
            assert result == "en"

    def test_language_codes(self):
        assert _detect_language("The United States announced") == "en"
        assert _detect_language("La France est un beau pays") == "fr"
