def evaluate(predictions: list[dict], expected: list[dict]) -> dict:
    def _metrics(pred_list, exp_list):
        pred_set = {(e["text"], e["label"], e["start"], e["end"]) for e in pred_list}
        exp_set = {(e["text"], e["label"], e["start"], e["end"]) for e in exp_list}
        tp = len(pred_set & exp_set)
        fp = len(pred_set - exp_set)
        fn = len(exp_set - pred_set)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        return {"precision": precision, "recall": recall, "f1": f1, "tp": tp, "fp": fp, "fn": fn}

    overall = _metrics(predictions, expected)

    labels = {e["label"] for e in predictions} | {e["label"] for e in expected}
    per_type = {}
    for label in sorted(labels):
        per_type[label] = _metrics(
            [e for e in predictions if e["label"] == label],
            [e for e in expected if e["label"] == label],
        )

    return {"overall": overall, "per_type": per_type}


def evaluate_corpus(corpus_path: str) -> dict:
    from src.evaluation.corpus import load_corpus
    from src.pipeline.detector import detect_language
    from src.pipeline.extractor import extract_location_mentions

    samples = load_corpus(corpus_path)
    all_predictions = []
    all_expected = []
    sample_results = []

    for sample in samples:
        text = sample["text"]
        lang = detect_language(text)
        predictions = extract_location_mentions(text, lang)

        sample_results.append({
            "text": (text[:80] + "...") if len(text) > 80 else text,
            "expected_language": sample["language"],
            "detected_language": lang,
        })

        all_predictions.extend(predictions)
        all_expected.extend(sample["entities"])

    metrics = evaluate(all_predictions, all_expected)

    return {
        "corpus_path": corpus_path,
        "sample_count": len(samples),
        "overall": metrics["overall"],
        "per_type": metrics["per_type"],
        "samples": sample_results,
    }
