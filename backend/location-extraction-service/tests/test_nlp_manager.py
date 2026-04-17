from src.pipeline.nlp_manager import get_ner_model


class TestNLPManager:
    """Tests for spaCy model manager."""

    def test_get_english_model(self):
        """Should load English spaCy model."""
        nlp = get_ner_model("en")
        assert nlp is not None

    def test_get_french_model(self):
        """Should load French spaCy model."""
        nlp = get_ner_model("fr")
        assert nlp is not None

    def test_model_caching(self):
        """Should cache models after first load."""
        from src.pipeline.nlp_manager import get_ner_model

        get_ner_model.cache_clear()
        nlp1 = get_ner_model("en")
        nlp2 = get_ner_model("en")
        assert nlp1 is nlp2

    def test_unknown_language_fallback(self):
        """Should fallback to English for unsupported languages."""
        nlp = get_ner_model("unsupported_lang")
        assert nlp is not None

    def test_concurrent_model_access(self):
        """Should handle concurrent access to models."""
        from src.pipeline.nlp_manager import get_ner_model

        get_ner_model.cache_clear()
        nlp1 = get_ner_model("en")
        nlp2 = get_ner_model("fr")
        assert nlp1 is not None
        assert nlp2 is not None
        assert nlp1 is not nlp2
