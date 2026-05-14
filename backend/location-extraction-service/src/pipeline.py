"""Stages 1-2: Language detection and NER location extraction via spaCy."""

import os
from dataclasses import dataclass
from functools import lru_cache

import langdetect
import spacy
from langdetect import DetectorFactory, LangDetectException

from src.models import EntityMention

DetectorFactory.seed = 0

_DEFAULT_LANGUAGE = "en"

_MODEL_MAP = {
    "en": os.getenv("SPACY_EN_MODEL", "en_core_web_sm"),
    "fr": os.getenv("SPACY_FR_MODEL", "fr_core_news_sm"),
}

_DEFAULT_MODEL = _MODEL_MAP["en"]

_LOCATION_LABELS = ("GPE", "LOC")


def _detect_language(text: str) -> str:
    if not text or not text.strip():
        return _DEFAULT_LANGUAGE

    try:
        langs = langdetect.detect_langs(text)
        if langs:
            return langs[0].lang
        return _DEFAULT_LANGUAGE
    except LangDetectException, IndexError, Exception:
        return _DEFAULT_LANGUAGE


def _cache_clear():
    _get_ner_model.cache_clear()


@lru_cache(maxsize=2)
def _get_ner_model(lang: str) -> spacy.Language:
    model_name = _MODEL_MAP.get(lang, _DEFAULT_MODEL)
    try:
        return spacy.load(model_name)
    except OSError:
        return spacy.load(_DEFAULT_MODEL)


def _extract_location_mentions(text: str, lang: str) -> list[EntityMention]:
    if not text or not text.strip():
        return []

    nlp = _get_ner_model(lang)
    doc = nlp(text)
    locations = []
    for ent in doc.ents:
        if ent.label_ in _LOCATION_LABELS:
            locations.append(
                EntityMention(
                    text=ent.text,
                    label=ent.label_,
                    start=ent.start_char,
                    end=ent.end_char,
                )
            )
    return locations


@dataclass
class NerResult:
    """Result of running stages 1-2 of the location extraction pipeline.

    Attributes:
        language: Detected language code (e.g. 'en', 'fr').
        entities: Extracted location entities as EntityMention records.
        model_name: Name of the spaCy model used for NER, if available.

    """

    language: str
    entities: list[EntityMention]
    model_name: str | None = None


class NerPipeline:
    """Composes language detection and NER extraction into a single step.

    This is the public seam for stages 1-2 of the pipeline.  Consumers
    (evaluation runner, API server, etc.) interact with the pipeline
    through this class, not the internal helper functions.
    """

    def run(self, text: str) -> NerResult:
        """Run language detection and NER extraction on input text.

        Args:
            text: Raw input text to analyze.

        Returns:
            NerResult containing detected language and extracted entities.

        """
        lang = _detect_language(text)
        ents = _extract_location_mentions(text, lang)
        model_name = _MODEL_MAP.get(lang)
        return NerResult(language=lang, entities=ents, model_name=model_name)
