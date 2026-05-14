from dataclasses import dataclass

from src.pipeline.detector import detect_language
from src.pipeline.extractor import extract_location_mentions
from src.pipeline.nlp_manager import MODEL_MAP


@dataclass
class NerResult:
    """Result of running stages 1-2 of the location extraction pipeline.

    Attributes:
        language: Detected language code (e.g. 'en', 'fr').
        entities: Extracted location entities, each with text, label, start, end.
        model_name: Name of the spaCy model used for NER.
    """

    language: str
    entities: list[dict]
    model_name: str | None = None


class NerPipeline:
    """Composes language detection and NER extraction into a single step.

    Wraps stages 1-2 of the pipeline behind a callable interface that can
    be injected into consumers like evaluation or the API server.
    """

    def run(self, text: str) -> NerResult:
        """Run language detection and NER extraction on input text.

        Args:
            text: Raw input text to analyze.

        Returns:
            NerResult containing detected language and extracted entities.
        """
        lang = detect_language(text)
        ents = extract_location_mentions(text, lang)
        model_name = MODEL_MAP.get(lang)
        return NerResult(language=lang, entities=ents, model_name=model_name)
