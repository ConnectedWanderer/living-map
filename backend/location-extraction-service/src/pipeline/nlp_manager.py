from functools import lru_cache

import spacy

MODEL_MAP = {
    "en": "en_core_web_trf",
    "fr": "fr_core_news_md",
}

DEFAULT_MODEL = MODEL_MAP["en"]


def cache_clear():
    """Clear the model cache."""
    get_ner_model.cache_clear()


@lru_cache(maxsize=2)
def get_ner_model(lang: str) -> spacy.Language:
    """Load and cache spaCy NER model for given language.

    Args:
        lang: Language code ('en', 'fr', etc.)

    Returns:
        Loaded spaCy model.

    Raises:
        OSError: If model cannot be loaded.
    """
    model_name = MODEL_MAP.get(lang, DEFAULT_MODEL)
    try:
        return spacy.load(model_name)
    except OSError:
        return spacy.load(DEFAULT_MODEL)
