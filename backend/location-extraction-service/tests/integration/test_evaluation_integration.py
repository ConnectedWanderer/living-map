"""Integration tests for evaluation orchestration (requires spaCy models)."""

import subprocess
import sys

import pytest

from src.evaluation.runner import evaluate_all_corpora, evaluate_corpus

pytestmark = pytest.mark.model_dependent


class TestEvaluateCorpus:
    def test_evaluate_corpus_returns_expected_structure(self, tmp_path):
        corpus_file = tmp_path / "test_corpus.json"
        corpus_file.write_text("""
        {
            "samples": [
                {
                    "text": "The meeting in Paris.",
                    "language": "en",
                    "entities": [
                        {"text": "Paris", "label": "GPE", "start": 16, "end": 21}
                    ]
                }
            ]
        }
        """)
        result = evaluate_corpus(str(corpus_file))
        assert result["corpus_path"] == str(corpus_file)
        assert result["sample_count"] == 1
        assert "overall" in result
        assert "per_type" in result
        assert "samples" in result
        for key in ("precision", "recall", "f1", "tp", "fp", "fn"):
            assert key in result["overall"]
        assert len(result["samples"]) == 1
        assert result["samples"][0]["expected_language"] == "en"
        assert result["samples"][0]["detected_language"] == "en"

    def test_evaluate_corpus_aggregates_multiple_samples(self, tmp_path):
        corpus_file = tmp_path / "multi.json"
        corpus_file.write_text("""
        {
            "samples": [
                {
                    "text": "Paris is in France.",
                    "language": "en",
                    "entities": [
                        {"text": "Paris", "label": "GPE", "start": 0, "end": 5},
                        {"text": "France", "label": "GPE", "start": 13, "end": 19}
                    ]
                },
                {
                    "text": "London is in the UK.",
                    "language": "en",
                    "entities": [
                        {"text": "London", "label": "GPE", "start": 0, "end": 6}
                    ]
                }
            ]
        }
        """)
        result = evaluate_corpus(str(corpus_file))
        assert result["sample_count"] == 2
        assert result["overall"]["tp"] >= 0
        assert result["overall"]["fp"] >= 0
        assert result["overall"]["fn"] >= 0


class TestEvaluateAllCorpora:
    def test_aggregate_equals_sum_of_per_corpus_metrics(self, tmp_path):
        corpus1 = tmp_path / "corpus_a.json"
        corpus1.write_text("""
        {
            "samples": [
                {
                    "text": "Paris is in France.",
                    "language": "en",
                    "entities": [
                        {"text": "Paris", "label": "GPE", "start": 0, "end": 5},
                        {"text": "France", "label": "GPE", "start": 13, "end": 19}
                    ]
                }
            ]
        }
        """)
        corpus2 = tmp_path / "corpus_b.json"
        corpus2.write_text("""
        {
            "samples": [
                {
                    "text": "London is a city.",
                    "language": "en",
                    "entities": [
                        {"text": "London", "label": "GPE", "start": 0, "end": 6}
                    ]
                }
            ]
        }
        """)

        result = evaluate_all_corpora(str(tmp_path))

        assert len(result["corpora"]) == 2

        agg_tp = result["aggregate"]["overall"]["tp"]
        agg_fp = result["aggregate"]["overall"]["fp"]
        agg_fn = result["aggregate"]["overall"]["fn"]

        sum_tp = sum(c["overall"]["tp"] for c in result["corpora"])
        sum_fp = sum(c["overall"]["fp"] for c in result["corpora"])
        sum_fn = sum(c["overall"]["fn"] for c in result["corpora"])

        assert agg_tp == sum_tp
        assert agg_fp == sum_fp
        assert agg_fn == sum_fn

    def test_empty_directory_returns_zeroed_metrics(self, tmp_path):
        result = evaluate_all_corpora(str(tmp_path))
        assert result["corpora"] == []
        assert result["merged_samples"] == []
        assert result["aggregate"]["overall"]["tp"] == 0
        assert result["aggregate"]["overall"]["fp"] == 0
        assert result["aggregate"]["overall"]["fn"] == 0
        assert result["aggregate"]["overall"]["precision"] == 0.0
        assert result["aggregate"]["overall"]["recall"] == 0.0
        assert result["aggregate"]["overall"]["f1"] == 0.0
        assert result["aggregate"]["per_type"] == {}

    def test_merged_samples_include_source_corpus_and_details(self, tmp_path):
        corpus_file = tmp_path / "test.json"
        corpus_file.write_text("""
        {
            "samples": [
                {
                    "text": "Paris is in France.",
                    "language": "en",
                    "entities": [
                        {"text": "Paris", "label": "GPE", "start": 0, "end": 5},
                        {"text": "France", "label": "GPE", "start": 13, "end": 19}
                    ]
                }
            ]
        }
        """)
        result = evaluate_all_corpora(str(tmp_path))
        assert len(result["merged_samples"]) == 1
        sample = result["merged_samples"][0]
        assert sample["source_corpus"] == "test.json"
        assert "expected_language" in sample
        assert "detected_language" in sample
        assert "expected_entities" in sample
        assert "predicted_entities" in sample
        assert "text" in sample


class TestCLI:
    def test_no_args_prints_synthesis_header(self):
        result = subprocess.run(
            [sys.executable, "-m", "src.evaluation"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0
        assert "Corpora:" in result.stdout
        assert "Aggregate Metrics" in result.stdout
        assert "Per-Corpus Summary" in result.stdout

    def test_single_corpus_prints_corpus_header(self, tmp_path):
        corpus_file = tmp_path / "corpus.json"
        corpus_file.write_text("""
        {
            "samples": [
                {
                    "text": "Paris is in France.",
                    "language": "en",
                    "entities": [
                        {"text": "Paris", "label": "GPE", "start": 0, "end": 5},
                        {"text": "France", "label": "GPE", "start": 13, "end": 19}
                    ]
                }
            ]
        }
        """)
        result = subprocess.run(
            [sys.executable, "-m", "src.evaluation", str(corpus_file)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0
        assert "Corpus:" in result.stdout
        assert "Overall Metrics:" in result.stdout
        assert "Per-Sample Results:" in result.stdout
