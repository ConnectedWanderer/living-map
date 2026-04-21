from unittest.mock import patch

from src.pipeline.detector import detect_language


class TestLanguageDetector:
    """Tests for language detection functionality."""

    def test_detect_english_text(self, sample_english_text):
        """Should detect English from English text."""
        result = detect_language(sample_english_text)
        assert result == "en"

    def test_detect_french_text(self, sample_french_text):
        """Should detect French from French text."""
        result = detect_language(sample_french_text)
        assert result == "fr"

    def test_detect_mixed_text_returns_dominant(self, mixed_english_heavy_text):
        """Should detect dominant language when text is mixed."""
        result = detect_language(mixed_english_heavy_text)
        assert result == "en"

    def test_detect_mixed_text_french_returns_dominant(self, mixed_french_heavy_text):
        """Should detect dominant language when text is mixed French-heavy."""
        result = detect_language(mixed_french_heavy_text)
        assert result == "fr"

    def test_fallback_to_english_on_empty_text(self):
        """Should fallback to English for empty text."""
        result = detect_language("")
        assert result == "en"

    def test_fallback_to_english_on_whitespace_only(self):
        """Should fallback to English for whitespace-only text."""
        result = detect_language("   \n\t  ")
        assert result == "en"

    def test_fallback_to_english_on_exception(self):
        """Should fallback to English when detection fails."""
        with patch("src.pipeline.detector.langdetect.detect_langs", side_effect=Exception("error")):
            result = detect_language("test text")
            assert result == "en"

    def test_language_codes(self):
        """Should return correct language codes for clear samples."""
        assert detect_language("The United States announced") == "en"
        assert detect_language("La France est un beau pays") == "fr"
