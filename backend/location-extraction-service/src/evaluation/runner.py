"""Evaluation orchestration, corpus loading, and multi-corpus aggregation."""

import dataclasses
import glob
import json
import os

from src.evaluation import _sum_metrics, evaluate, evaluate_event_location, evaluate_geocoding
from src.orchestrator import LocationPipeline
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


def run_pipeline_on_corpus(
    corpus_path: str,
    pipeline: NerPipeline | None = None,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Run stages 1-2 pipeline on all samples in a corpus file.

    Separated from evaluate_corpus so it can be reused for geocoding
    evaluation without duplicating the corpus loading and pipeline
    orchestration logic.

    Args:
        corpus_path: Path to corpus JSON file.
        pipeline: NerPipeline instance (defaults to real pipeline if omitted).

    Returns:
        Tuple of (all_predictions, all_expected, sample_results) where each
        element is a list of dicts. all_predictions and all_expected are flat
        lists of entity dicts across all samples. sample_results is a list of
        per-sample result dicts with text, languages, and entity lists.

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

    return all_predictions, all_expected, sample_results


def evaluate_corpus(corpus_path: str, pipeline: NerPipeline | None = None) -> dict:
    """Run stages 1-2 evaluation on a single corpus file.

    Thin composition of run_pipeline_on_corpus + evaluate.

    Args:
        corpus_path: Path to corpus JSON file.
        pipeline: NerPipeline instance (defaults to real pipeline if omitted).

    Returns:
        Dict with corpus_path, sample_count, overall metrics, per_type metrics,
        and per-sample results including expected vs predicted entities.

    """
    predictions, expected, sample_results = run_pipeline_on_corpus(corpus_path, pipeline)
    metrics = evaluate(predictions, expected)

    return {
        "corpus_path": corpus_path,
        "sample_count": len(sample_results),
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


def run_full_pipeline_on_corpus(
    corpus_path: str,
    pipeline: LocationPipeline | None = None,
) -> tuple[list[dict], list[dict], list[dict | None], list[dict | None], list[dict]]:
    """Run full 4-stage pipeline on all samples in a corpus file.

    Loads corpus samples, runs the full LocationPipeline on each, and returns
    aggregated predicted vs expected geocoded locations and event locations.

    Args:
        corpus_path: Path to corpus JSON file.
        pipeline: LocationPipeline instance (defaults to real pipeline if omitted).

    Returns:
        Tuple of (all_predicted_geocoded, all_expected_geocoded,
        all_predicted_events, all_expected_events, sample_results).

    """
    pipeline = pipeline or LocationPipeline()
    samples = load_corpus(corpus_path)

    all_predicted_geocoded = []
    all_expected_geocoded = []
    all_predicted_events: list[dict | None] = []
    all_expected_events: list[dict | None] = []
    sample_results = []

    for sample in samples:
        text = sample["text"]
        result = pipeline.run(text)

        predicted_geocoded = [
            {
                "text": loc.text,
                "lat": loc.lat,
                "lon": loc.lon,
                "country": loc.country,
            }
            for loc in result.all_locations
        ]

        expected_geocoded = sample.get("expected_geocoded_locations", [])

        predicted_event = None
        if result.event_location:
            predicted_event = {
                "text": result.event_location.text,
                "lat": result.event_location.lat,
                "lon": result.event_location.lon,
                "country": result.event_location.country,
                "confidence": result.event_location.confidence,
            }

        expected_event = sample.get("expected_event_location")

        sample_results.append(
            {
                "text": (text[:80] + "...") if len(text) > 80 else text,
                "predicted_geocoded": predicted_geocoded,
                "expected_geocoded": expected_geocoded,
                "predicted_event_location": predicted_event,
                "expected_event_location": expected_event,
            }
        )

        all_predicted_geocoded.extend(predicted_geocoded)
        all_expected_geocoded.extend(expected_geocoded)
        all_predicted_events.append(predicted_event)
        all_expected_events.append(expected_event)

    return (
        all_predicted_geocoded,
        all_expected_geocoded,
        all_predicted_events,
        all_expected_events,
        sample_results,
    )


def evaluate_geocoding_corpus(
    corpus_path: str,
    pipeline: LocationPipeline | None = None,
) -> dict:
    """Run geocoding evaluation on a single corpus file.

    Args:
        corpus_path: Path to corpus JSON file.
        pipeline: LocationPipeline instance (defaults to real pipeline if omitted).

    Returns:
        Dict with corpus_path, sample_count, geocoding metrics, event location
        metrics, and per-sample results.

    """
    predicted_geo, expected_geo, predicted_events, expected_events, sample_results = (
        run_full_pipeline_on_corpus(corpus_path, pipeline)
    )

    geocoding_metrics = evaluate_geocoding(predicted_geo, expected_geo)

    event_results = [
        evaluate_event_location(pred, exp)
        for pred, exp in zip(predicted_events, expected_events, strict=False)
    ]
    event_correct = sum(1 for r in event_results if r.get("correct"))
    event_expected = sum(1 for r in event_results if r.get("expected"))

    return {
        "corpus_path": corpus_path,
        "sample_count": len(sample_results),
        "geocoding": geocoding_metrics,
        "event_location": {
            "accuracy": event_correct / event_expected if event_expected > 0 else 0.0,
            "correct": event_correct,
            "expected": event_expected,
        },
        "samples": sample_results,
    }


def evaluate_geocoding_all_corpora(corpus_dir: str = DEFAULT_CORPUS_DIR) -> dict:
    """Run geocoding evaluation across all corpus files in a directory.

    Args:
        corpus_dir: Directory containing corpus JSON files.

    Returns:
        Dict with aggregate metrics and per-corpus results.

    """
    corpus_paths = discover_corpora(corpus_dir)
    corpora = []

    for path in corpus_paths:
        result = evaluate_geocoding_corpus(path)
        corpora.append(result)

    if not corpora:
        return {
            "corpora": [],
            "aggregate": {
                "geocoding": {
                    "geocoding_rate": 0.0,
                    "country_accuracy": 0.0,
                    "total_expected": 0,
                    "geocoded": 0,
                    "country_matches": 0,
                },
                "event_location": {"accuracy": 0.0, "correct": 0, "expected": 0},
            },
        }

    total_expected = sum(c["geocoding"]["total_expected"] for c in corpora)
    total_geocoded = sum(c["geocoding"]["geocoded"] for c in corpora)
    total_country_matches = sum(c["geocoding"]["country_matches"] for c in corpora)
    total_event_correct = sum(c["event_location"]["correct"] for c in corpora)
    total_event_expected = sum(c["event_location"]["expected"] for c in corpora)

    return {
        "corpora": corpora,
        "aggregate": {
            "geocoding": {
                "geocoding_rate": total_geocoded / total_expected if total_expected > 0 else 0.0,
                "country_accuracy": total_country_matches / total_geocoded
                if total_geocoded > 0
                else 0.0,
                "total_expected": total_expected,
                "geocoded": total_geocoded,
                "country_matches": total_country_matches,
            },
            "event_location": {
                "accuracy": total_event_correct / total_event_expected
                if total_event_expected > 0
                else 0.0,
                "correct": total_event_correct,
                "expected": total_event_expected,
            },
        },
    }
