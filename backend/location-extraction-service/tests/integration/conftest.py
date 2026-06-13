import os

import pytest
import spacy

_SPACY_MODELS = {
    "en": os.getenv("SPACY_EN_MODEL", "en_core_web_sm"),
    "fr": os.getenv("SPACY_FR_MODEL", "fr_core_news_sm"),
}


@pytest.fixture(scope="session")
def small_nlp_models():
    os.environ["SPACY_EN_MODEL"] = "en_core_web_sm"
    os.environ["SPACY_FR_MODEL"] = "fr_core_news_sm"

    missing = []
    for _lang, model in _SPACY_MODELS.items():
        try:
            spacy.load(model)
        except OSError:
            missing.append(model)
    if missing:
        models = " ".join(missing)
        pytest.skip(
            f"spaCy model(s) not found: {models}. Run: uv run python -m spacy download {models}"
        )
