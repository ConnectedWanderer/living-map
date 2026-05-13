import json

import pytest

from src.evaluation import evaluate
from src.evaluation.corpus import load_corpus


class TestEvaluate:
    def test_all_predictions_match_exactly(self):
        predictions = [
            {"text": "Paris", "label": "GPE", "start": 0, "end": 5},
        ]
        expected = [
            {"text": "Paris", "label": "GPE", "start": 0, "end": 5},
        ]
        result = evaluate(predictions, expected)
        overall = result["overall"]
        assert overall["precision"] == 1.0
        assert overall["recall"] == 1.0
        assert overall["f1"] == 1.0
        assert overall["tp"] == 1
        assert overall["fp"] == 0
        assert overall["fn"] == 0

    def test_no_matches_returns_zero_metrics(self):
        predictions = [
            {"text": "Paris", "label": "GPE", "start": 0, "end": 5},
        ]
        expected = [
            {"text": "London", "label": "GPE", "start": 0, "end": 6},
        ]
        result = evaluate(predictions, expected)
        overall = result["overall"]
        assert overall["precision"] == 0.0
        assert overall["recall"] == 0.0
        assert overall["f1"] == 0.0
        assert overall["tp"] == 0
        assert overall["fp"] == 1
        assert overall["fn"] == 1

    def test_text_mismatch(self):
        predictions = [
            {"text": "Paris", "label": "GPE", "start": 0, "end": 5},
        ]
        expected = [
            {"text": "Paries", "label": "GPE", "start": 0, "end": 5},
        ]
        result = evaluate(predictions, expected)
        assert result["overall"]["tp"] == 0

    def test_start_offset_mismatch(self):
        predictions = [
            {"text": "Paris", "label": "GPE", "start": 0, "end": 5},
        ]
        expected = [
            {"text": "Paris", "label": "GPE", "start": 2, "end": 5},
        ]
        result = evaluate(predictions, expected)
        assert result["overall"]["tp"] == 0

    def test_end_offset_mismatch(self):
        predictions = [
            {"text": "Paris", "label": "GPE", "start": 0, "end": 5},
        ]
        expected = [
            {"text": "Paris", "label": "GPE", "start": 0, "end": 7},
        ]
        result = evaluate(predictions, expected)
        assert result["overall"]["tp"] == 0

    def test_label_mismatch(self):
        predictions = [
            {"text": "Paris", "label": "GPE", "start": 0, "end": 5},
        ]
        expected = [
            {"text": "Paris", "label": "LOC", "start": 0, "end": 5},
        ]
        result = evaluate(predictions, expected)
        assert result["overall"]["tp"] == 0

    def test_partial_matches(self):
        predictions = [
            {"text": "Paris", "label": "GPE", "start": 0, "end": 5},
            {"text": "Berlin", "label": "GPE", "start": 10, "end": 16},
        ]
        expected = [
            {"text": "Paris", "label": "GPE", "start": 0, "end": 5},
            {"text": "Madrid", "label": "GPE", "start": 20, "end": 26},
        ]
        result = evaluate(predictions, expected)
        overall = result["overall"]
        assert overall["tp"] == 1
        assert overall["fp"] == 1
        assert overall["fn"] == 1
        assert overall["precision"] == 0.5
        assert overall["recall"] == 0.5
        assert overall["f1"] == 0.5

    def test_multiple_matches(self):
        predictions = [
            {"text": "Paris", "label": "GPE", "start": 0, "end": 5},
            {"text": "London", "label": "GPE", "start": 10, "end": 16},
            {"text": "Berlin", "label": "GPE", "start": 20, "end": 26},
        ]
        expected = [
            {"text": "Paris", "label": "GPE", "start": 0, "end": 5},
            {"text": "London", "label": "GPE", "start": 10, "end": 16},
        ]
        result = evaluate(predictions, expected)
        assert result["overall"]["tp"] == 2
        assert result["overall"]["fp"] == 1
        assert result["overall"]["fn"] == 0
        assert result["overall"]["precision"] == 2 / 3
        assert result["overall"]["recall"] == 1.0

    def test_empty_predictions(self):
        result = evaluate([], [{"text": "Paris", "label": "GPE", "start": 0, "end": 5}])
        overall = result["overall"]
        assert overall["tp"] == 0
        assert overall["fp"] == 0
        assert overall["fn"] == 1
        assert overall["precision"] == 0.0
        assert overall["recall"] == 0.0
        assert overall["f1"] == 0.0

    def test_empty_expected(self):
        result = evaluate([{"text": "Paris", "label": "GPE", "start": 0, "end": 5}], [])
        overall = result["overall"]
        assert overall["tp"] == 0
        assert overall["fp"] == 1
        assert overall["fn"] == 0
        assert overall["precision"] == 0.0
        assert overall["recall"] == 0.0
        assert overall["f1"] == 0.0

    def test_both_empty(self):
        result = evaluate([], [])
        overall = result["overall"]
        assert overall["tp"] == 0
        assert overall["fp"] == 0
        assert overall["fn"] == 0
        assert overall["precision"] == 0.0
        assert overall["recall"] == 0.0
        assert overall["f1"] == 0.0

    def test_per_type_gpe(self):
        predictions = [
            {"text": "Paris", "label": "GPE", "start": 0, "end": 5},
            {"text": "London", "label": "GPE", "start": 10, "end": 16},
        ]
        expected = [
            {"text": "Paris", "label": "GPE", "start": 0, "end": 5},
            {"text": "Madrid", "label": "GPE", "start": 20, "end": 26},
        ]
        result = evaluate(predictions, expected)
        assert "GPE" in result["per_type"]
        assert result["per_type"]["GPE"]["tp"] == 1
        assert result["per_type"]["GPE"]["fp"] == 1
        assert result["per_type"]["GPE"]["fn"] == 1

    def test_per_type_loc(self):
        predictions = [
            {"text": "Seine", "label": "LOC", "start": 0, "end": 5},
        ]
        expected = [
            {"text": "Seine", "label": "LOC", "start": 0, "end": 5},
            {"text": "Alps", "label": "LOC", "start": 10, "end": 14},
        ]
        result = evaluate(predictions, expected)
        assert "LOC" in result["per_type"]
        assert result["per_type"]["LOC"]["tp"] == 1
        assert result["per_type"]["LOC"]["fp"] == 0
        assert result["per_type"]["LOC"]["fn"] == 1

    def test_per_type_separates_gpe_and_loc(self):
        predictions = [
            {"text": "Paris", "label": "GPE", "start": 0, "end": 5},
            {"text": "Seine", "label": "LOC", "start": 10, "end": 15},
            {"text": "Berlin", "label": "GPE", "start": 20, "end": 26},
        ]
        expected = [
            {"text": "Paris", "label": "GPE", "start": 0, "end": 5},
            {"text": "Seine", "label": "LOC", "start": 10, "end": 15},
        ]
        result = evaluate(predictions, expected)
        assert result["per_type"]["GPE"]["tp"] == 1
        assert result["per_type"]["GPE"]["fp"] == 1
        assert result["per_type"]["GPE"]["fn"] == 0
        assert result["per_type"]["LOC"]["tp"] == 1
        assert result["per_type"]["LOC"]["fp"] == 0
        assert result["per_type"]["LOC"]["fn"] == 0

    def test_per_type_includes_only_types_present(self):
        result = evaluate(
            [{"text": "Paris", "label": "GPE", "start": 0, "end": 5}],
            [{"text": "Paris", "label": "GPE", "start": 0, "end": 5}],
        )
        assert "GPE" in result["per_type"]
        assert "LOC" not in result["per_type"]


class TestLoadCorpus:
    def test_load_corpus_returns_samples(self, tmp_path):
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
        samples = load_corpus(str(corpus_file))
        assert len(samples) == 1
        assert samples[0]["text"] == "Paris is in France."
        assert samples[0]["language"] == "en"
        assert len(samples[0]["entities"]) == 2

    def test_load_corpus_empty_entities(self, tmp_path):
        corpus_file = tmp_path / "empty_entities.json"
        corpus_file.write_text("""
        {
            "samples": [
                {"text": "Hello world.", "language": "en", "entities": []}
            ]
        }
        """)
        samples = load_corpus(str(corpus_file))
        assert len(samples) == 1
        assert samples[0]["entities"] == []

    def test_load_corpus_multiple_samples(self, tmp_path):
        corpus_file = tmp_path / "multi.json"
        corpus_file.write_text("""
        {
            "samples": [
                {"text": "First.", "language": "en", "entities": []},
                {"text": "Second.", "language": "fr", "entities": []}
            ]
        }
        """)
        assert len(load_corpus(str(corpus_file))) == 2

    def test_load_corpus_missing_file(self):
        with pytest.raises(FileNotFoundError):
            load_corpus("/nonexistent/path.json")

    def test_load_corpus_invalid_json(self, tmp_path):
        corpus_file = tmp_path / "bad.json"
        corpus_file.write_text("not json")
        with pytest.raises(json.JSONDecodeError):
            load_corpus(str(corpus_file))
