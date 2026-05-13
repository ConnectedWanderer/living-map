import glob
import os

DEFAULT_CORPUS_DIR = "tests/corpus"


def _compute_rates(tp: int, fp: int, fn: int) -> dict:
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return {"precision": precision, "recall": recall, "f1": f1, "tp": tp, "fp": fp, "fn": fn}


def evaluate(predictions: list[dict], expected: list[dict]) -> dict:
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

        sample_results.append(
            {
                "text": (text[:80] + "...") if len(text) > 80 else text,
                "expected_language": sample["language"],
                "detected_language": lang,
                "expected_entities": sample["entities"],
                "predicted_entities": predictions,
            }
        )

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


def discover_corpora(corpus_dir: str = DEFAULT_CORPUS_DIR) -> list[str]:
    return sorted(glob.glob(os.path.join(corpus_dir, "*.json")))


def _sum_metrics(metrics_list: list[dict]) -> dict:
    return _compute_rates(
        sum(m["tp"] for m in metrics_list),
        sum(m["fp"] for m in metrics_list),
        sum(m["fn"] for m in metrics_list),
    )


def evaluate_all_corpora(corpus_dir: str = DEFAULT_CORPUS_DIR) -> dict:
    corpus_paths = discover_corpora(corpus_dir)
    corpora = []
    merged_samples = []

    for path in corpus_paths:
        result = evaluate_corpus(path)
        corpora.append(result)
        for s in result["samples"]:
            merged_samples.append(
                {
                    "source_corpus": os.path.basename(path),
                    **s,
                }
            )

    if not corpora:
        return {
            "corpora": [],
            "aggregate": {
                "overall": {"precision": 0.0, "recall": 0.0, "f1": 0.0, "tp": 0, "fp": 0, "fn": 0},
                "per_type": {},
            },
            "merged_samples": [],
        }

    overall_metrics = _sum_metrics([c["overall"] for c in corpora])

    all_labels = sorted({lab for c in corpora for lab in c["per_type"]})
    per_type_metrics = {}
    for label in all_labels:
        per_corpus = [c["per_type"].get(label) for c in corpora if label in c["per_type"]]
        per_type_metrics[label] = _sum_metrics(per_corpus)

    return {
        "corpora": corpora,
        "aggregate": {
            "overall": overall_metrics,
            "per_type": per_type_metrics,
        },
        "merged_samples": merged_samples,
    }
