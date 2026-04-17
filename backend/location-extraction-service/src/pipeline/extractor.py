from src.pipeline.nlp_manager import get_ner_model

LOCATION_LABELS = ("GPE", "LOC")


def extract_location_mentions(text: str, lang: str) -> list[dict]:
    """Extract location mentions (GPE, LOC) from text.

    Args:
        text: Input text to analyze.
        lang: Language code for NER model.

    Returns:
        List of location entities with text, label, start, end.
    """
    if not text or not text.strip():
        return []

    nlp = get_ner_model(lang)
    doc = nlp(text)
    locations = []
    for ent in doc.ents:
        if ent.label_ in LOCATION_LABELS:
            locations.append(
                {
                    "text": ent.text,
                    "label": ent.label_,
                    "start": ent.start_char,
                    "end": ent.end_char,
                }
            )
    return locations
