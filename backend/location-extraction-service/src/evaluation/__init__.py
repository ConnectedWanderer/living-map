"""NER quality metrics: precision, recall, F1 computation."""


def _compute_rates(tp: int, fp: int, fn: int) -> dict:
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return {"precision": precision, "recall": recall, "f1": f1, "tp": tp, "fp": fp, "fn": fn}


def evaluate(predictions: list[dict], expected: list[dict]) -> dict:
    """Compute entity-level precision, recall, and harmonic mean (F1).

    Compares predicted entities against expected entities using
    exact-match criteria: text, label, start, and end must all match.

    Args:
        predictions: List of predicted entity dicts with text, label, start, end.
        expected: List of expected entity dicts with text, label, start, end.

    Returns:
        Dict with 'overall' metrics and 'per_type' breakdown keyed by label.

    """

    def _metrics(pred_list, exp_list):
        pred_set = {(e["text"], e["label"], e["start"], e["end"]) for e in pred_list}
        exp_set = {(e["text"], e["label"], e["start"], e["end"]) for e in exp_list}
        return _compute_rates(
            len(pred_set & exp_set),
            len(pred_set - exp_set),
            len(exp_set - pred_set),
        )

    overall = _metrics(predictions, expected)

    labels = {e["label"] for e in predictions} | {e["label"] for e in expected}
    per_type = {}
    for label in sorted(labels):
        per_type[label] = _metrics(
            [e for e in predictions if e["label"] == label],
            [e for e in expected if e["label"] == label],
        )

    return {"overall": overall, "per_type": per_type}


def _sum_metrics(metrics_list: list[dict]) -> dict:
    return _compute_rates(
        sum(m["tp"] for m in metrics_list),
        sum(m["fp"] for m in metrics_list),
        sum(m["fn"] for m in metrics_list),
    )


def evaluate_geocoding(predictions: list[dict], expected: list[dict]) -> dict:
    """Evaluate geocoding accuracy against expected locations.

    Compares predicted geocoded locations (from the pipeline output) against
    expected locations (from corpus annotations). Matches by place name text.

    Args:
        predictions: List of predicted location dicts with 'text' and 'country'.
        expected: List of expected location dicts with 'text' and 'country'.

    Returns:
        Dict with geocoding_rate, country_accuracy, total_expected, geocoded,
        and country_matches.

    """
    pred_by_text = {p["text"]: p for p in predictions}

    total = len(expected)
    geocoded = 0
    country_checkable = 0
    country_matches = 0

    for exp in expected:
        text = exp["text"]
        pred = pred_by_text.get(text)
        if pred is not None:
            geocoded += 1
            if "country" in exp:
                country_checkable += 1
                if pred.get("country") == exp["country"]:
                    country_matches += 1

    return {
        "geocoding_rate": geocoded / total if total > 0 else 0.0,
        "country_accuracy": country_matches / country_checkable if country_checkable > 0 else 1.0,
        "total_expected": total,
        "geocoded": geocoded,
        "country_matches": country_matches,
    }


def evaluate_event_location(predicted: dict | None, expected: dict | None) -> dict:
    """Evaluate event location inference accuracy.

    Args:
        predicted: Predicted event location dict with 'text', 'country' or None.
        expected: Expected event location dict with 'text', 'country' or None.

    Returns:
        Dict with expected (bool), correct (bool or None), text_match, and
        country_match.

    """
    if expected is None:
        return {"expected": False, "correct": None, "text_match": None, "country_match": None}

    text_match = predicted is not None and predicted.get("text") == expected.get("text")
    country_match = predicted is not None and predicted.get("country") == expected.get("country")

    return {
        "expected": True,
        "correct": text_match and country_match,
        "text_match": text_match,
        "country_match": country_match,
    }
