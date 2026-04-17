import langdetect
from langdetect import DetectorFactory, LangDetectException

# Ensure deterministic language detection
DetectorFactory.seed = 0


def detect_language(text: str) -> str:
    """Detect language from text.

    Args:
        text: Input text to analyze.

    Returns:
        Language code ('en' or 'fr' for example).

    Raises:
        LangDetectException: When detection fails, falls back to 'en'.
    """
    if not text or not text.strip():
        return "en"

    try:
        langs = langdetect.detect_langs(text)
        if langs:
            return langs[0].lang
        return "en"
    except LangDetectException, IndexError, Exception:
        return "en"
