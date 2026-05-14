"""Evaluation orchestration, corpus loading, and multi-corpus aggregation."""

import dataclasses
import glob
import json
import os

from src.evaluation import _sum_metrics, evaluate
from src.pipeline import NerPipeline

DEFAULT_CORPUS_DIR = "tests/corpus"


def load_corpus(path: str) -> list[dict]:
    """Load evaluation corpus samples from a JSON file.

    Args:
        path: Path to corpus JSON file.

    Returns:
        List of sample dicts, each with text, language, and entities.

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.

    """
    with open(path) as f:
        data = json.load(f)
    return data["samples"]


def discover_corpora(corpus_dir: str = DEFAULT_CORPUS_DIR) -> list[str]:
    """Find all JSON corpus files in a directory.

    Args:
        corpus_dir: Directory to search (defaults to tests/corpus).

    Returns:
        Sorted list of absolute paths to .json files.

    """
    return sorted(glob.glob(os.path.join(corpus_dir, "*.json")))


def evaluate_corpus(corpus_path: str, pipeline: NerPipeline | None = None) -> dict:
    """Run stages 1-2 evaluation on a single corpus file.

    Loads corpus samples, runs language detection and NER via the pipeline,
    and computes precision, recall, and harmonic mean (F1) against expected annotations.

    Args:
        corpus_path: Path to corpus JSON file.
        pipeline: NerPipeline instance (defaults to real pipeline if omitted).

    Returns:
        Dict with corpus_path, sample_count, overall metrics, per_type metrics,
        and per-sample results including expected vs predicted entities.

    """
    pipeline = pipeline or NerPipeline()
    samples = load_corpus(corpus_path)
    all_predictions = []
    all_expected = []
    sample_results = []

    for sample in samples:
        text = sample["text"]
        result = pipeline.run(text)
        predictions = [dataclasses.asdict(e) for e in result.entities]

        sample_results.append(
            {
                "text": (text[:80] + "...") if len(text) > 80 else text,
                "expected_language": sample["language"],
                "detected_language": result.language,
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


def evaluate_all_corpora(corpus_dir: str = DEFAULT_CORPUS_DIR) -> dict:
    """Run stages 1-2 evaluation across all corpus files in a directory.

    Discovers all JSON corpus files, evaluates each individually, and
    produces aggregate metrics across all corpora plus a merged sample list.

    Args:
        corpus_dir: Directory containing corpus JSON files.

    Returns:
        Dict with aggregate overall/per_type metrics, per-corpus results,
        and merged_samples with source_corpus metadata.

    """
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
