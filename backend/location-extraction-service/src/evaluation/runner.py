"""Evaluation orchestration, corpus loading, and multi-corpus aggregation."""

import dataclasses
import glob
import importlib
import json
import os

from ..disambiguator import DisambiguatePipeline
from ..geocoding import GeoPipeline
from ..models import EntityMention
from ..orchestrator import LocationPipeline
from ..pipeline import NerPipeline
from . import _sum_metrics, evaluate, evaluate_event_location, evaluate_geocoding

DEFAULT_CORPUS_DIR = "tests/corpus"

_GENERATED_CORPORA: dict[str, str] = {
    "en_wikiann.json": "src.evaluation.converters.en_wikiann",
    "fr_wikiner_gold.json": "src.evaluation.converters.wikiner_fr",
}


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
    """Find all JSON corpus files in a directory, generating large corpora if missing.

    Discovers existing files via glob, then checks for expected large corpus
    files that don't exist yet. If found missing, attempts to import the
    corresponding conversion module (from ``scripts/``) and generate the
    corpus on demand. Requires ``datasets`` — if unavailable, silently skips
    and returns only hand-written corpora.

    Args:
        corpus_dir: Directory to search (defaults to tests/corpus).

    Returns:
        Sorted list of absolute paths to .json files.

    """
    paths = set(glob.glob(os.path.join(corpus_dir, "*.json")))

    for filename, module_path in _GENERATED_CORPORA.items():
        filepath = os.path.join(corpus_dir, filename)
        if filepath in paths:
            continue
        try:
            mod = importlib.import_module(module_path)
            mod.convert(filepath)
            paths.add(filepath)
        except ImportError:
            continue

    return sorted(paths)


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
                "text": ent.text,
                "lat": ent.geocoding.lat if ent.geocoding else None,
                "lon": ent.geocoding.lon if ent.geocoding else None,
                "country": ent.geocoding.country if ent.geocoding else None,
            }
            for ent in result.all_entities
            if ent.geocoded
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


def run_geocoding_pipeline_on_corpus(
    corpus_path: str,
    geo_pipeline: GeoPipeline | None = None,
    dis_pipeline: DisambiguatePipeline | None = None,
) -> tuple[list[dict], list[dict], list[dict | None], list[dict | None], list[dict]]:
    """Run geocoding pipeline (stages 3-4) on corpus expected entities (bypasses NER).

    Loads corpus samples and feeds the ground-truth ``entities`` directly into
    GeoPipeline, then DisambiguatePipeline, so that geocoding accuracy is
    measured independently of NER quality.

    Args:
        corpus_path: Path to corpus JSON file.
        geo_pipeline: GeoPipeline instance (defaults to real pipeline).
        dis_pipeline: DisambiguatePipeline instance (defaults to real pipeline).

    Returns:
        Tuple of (all_predicted_geocoded, all_expected_geocoded,
        all_predicted_events, all_expected_events, sample_results).

    """
    geo_pipeline = geo_pipeline or GeoPipeline()
    dis_pipeline = dis_pipeline or DisambiguatePipeline()
    samples = load_corpus(corpus_path)

    all_predicted_geocoded = []
    all_expected_geocoded = []
    all_predicted_events: list[dict | None] = []
    all_expected_events: list[dict | None] = []
    sample_results = []

    for sample in samples:
        text = sample["text"]
        entities = [EntityMention(**e) for e in sample["entities"]]

        geo_result = geo_pipeline.run(entities)
        dis_result = dis_pipeline.run(geo_result.locations, text)

        predicted_geocoded = [
            {
                "text": loc.text,
                "lat": loc.lat,
                "lon": loc.lon,
                "country": loc.country,
            }
            for loc in geo_result.locations
        ]

        expected_geocoded = sample.get("expected_geocoded_locations", [])

        predicted_event = None
        if dis_result.event_location:
            predicted_event = {
                "text": dis_result.event_location.text,
                "lat": dis_result.event_location.lat,
                "lon": dis_result.event_location.lon,
                "country": dis_result.event_location.country,
                "confidence": dis_result.event_location.confidence,
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


def evaluate_geocoding_decoupled_corpus(
    corpus_path: str,
    geo_pipeline: GeoPipeline | None = None,
    dis_pipeline: DisambiguatePipeline | None = None,
) -> dict:
    """Run decoupled geocoding evaluation on a single corpus file.

    Args:
        corpus_path: Path to corpus JSON file.
        geo_pipeline: GeoPipeline instance.
        dis_pipeline: DisambiguatePipeline instance.

    Returns:
        Dict with corpus_path, sample_count, geocoding metrics, event location
        metrics, and per-sample results.

    """
    predicted_geo, expected_geo, predicted_events, expected_events, sample_results = (
        run_geocoding_pipeline_on_corpus(corpus_path, geo_pipeline, dis_pipeline)
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


def _sum_distance_metrics(metrics_list: list[dict]) -> dict:
    """Aggregate distance metrics across multiple corpora by summing distances.

    Args:
        metrics_list: List of geocoding metric dicts with distance fields.

    Returns:
        Single aggregated distance-metric dict.

    """
    n = sum(m["distance_checkable"] for _, m in metrics_list)
    if n == 0:
        return {
            "mean_distance_km": 0.0,
            "within_1km": 0.0,
            "within_10km": 0.0,
            "within_100km": 0.0,
            "distance_checkable": 0,
        }

    total_distance_sum = 0.0
    total_1km = 0
    total_10km = 0
    total_100km = 0
    for _, m in metrics_list:
        total_distance_sum += m["mean_distance_km"] * m["distance_checkable"]
        total_1km += round(m["within_1km"] * m["distance_checkable"])
        total_10km += round(m["within_10km"] * m["distance_checkable"])
        total_100km += round(m["within_100km"] * m["distance_checkable"])

    return {
        "mean_distance_km": total_distance_sum / n,
        "within_1km": total_1km / n,
        "within_10km": total_10km / n,
        "within_100km": total_100km / n,
        "distance_checkable": n,
    }


def evaluate_geocoding_decoupled_all_corpora(corpus_dir: str = DEFAULT_CORPUS_DIR) -> dict:
    """Run decoupled geocoding evaluation across all corpus files.

    Args:
        corpus_dir: Directory containing corpus JSON files.

    Returns:
        Dict with aggregate metrics and per-corpus results.

    """
    corpus_paths = discover_corpora(corpus_dir)
    corpora = []

    for path in corpus_paths:
        result = evaluate_geocoding_decoupled_corpus(path)
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
                    "mean_distance_km": 0.0,
                    "within_1km": 0.0,
                    "within_10km": 0.0,
                    "within_100km": 0.0,
                    "distance_checkable": 0,
                },
                "event_location": {"accuracy": 0.0, "correct": 0, "expected": 0},
            },
        }

    total_expected = sum(c["geocoding"]["total_expected"] for c in corpora)
    total_geocoded = sum(c["geocoding"]["geocoded"] for c in corpora)
    total_country_matches = sum(c["geocoding"]["country_matches"] for c in corpora)
    total_event_correct = sum(c["event_location"]["correct"] for c in corpora)
    total_event_expected = sum(c["event_location"]["expected"] for c in corpora)

    distance_metrics = _sum_distance_metrics([(c, c["geocoding"]) for c in corpora])

    geo_aggregate = {
        "geocoding_rate": total_geocoded / total_expected if total_expected > 0 else 0.0,
        "country_accuracy": total_country_matches / total_geocoded if total_geocoded > 0 else 0.0,
        "total_expected": total_expected,
        "geocoded": total_geocoded,
        "country_matches": total_country_matches,
    }
    geo_aggregate.update(distance_metrics)

    return {
        "corpora": corpora,
        "aggregate": {
            "geocoding": geo_aggregate,
            "event_location": {
                "accuracy": total_event_correct / total_event_expected
                if total_event_expected > 0
                else 0.0,
                "correct": total_event_correct,
                "expected": total_event_expected,
            },
        },
    }
