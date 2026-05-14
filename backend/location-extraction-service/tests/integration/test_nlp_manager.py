import pytest

from src.pipeline import _get_ner_model

pytestmark = pytest.mark.model_dependent


class TestNLPManager:
    def test_get_english_model(self):
        nlp = _get_ner_model("en")
        assert nlp is not None

    def test_get_french_model(self):
        nlp = _get_ner_model("fr")
        assert nlp is not None

    def test_model_caching(self):
        from src.pipeline import _get_ner_model

        _get_ner_model.cache_clear()
        nlp1 = _get_ner_model("en")
        nlp2 = _get_ner_model("en")
        assert nlp1 is nlp2

    def test_unknown_language_fallback(self):
        nlp = _get_ner_model("unsupported_lang")
        assert nlp is not None

    def test_concurrent_model_access(self):
        from src.pipeline import _get_ner_model

        _get_ner_model.cache_clear()
        nlp1 = _get_ner_model("en")
        nlp2 = _get_ner_model("fr")
        assert nlp1 is not None
        assert nlp2 is not None
        assert nlp1 is not nlp2
