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
