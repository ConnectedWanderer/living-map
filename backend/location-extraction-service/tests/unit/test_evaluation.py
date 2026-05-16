import json

import pytest

from src.evaluation import evaluate, evaluate_event_location, evaluate_geocoding, haversine
from src.evaluation.runner import discover_corpora, load_corpus


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


class TestDiscoverCorpora:
    def test_returns_json_files_sorted(self, tmp_path):
        (tmp_path / "b_file.json").write_text("{}")
        (tmp_path / "a_file.json").write_text("{}")
        (tmp_path / "not_json.txt").write_text("{}")
        result = discover_corpora(str(tmp_path))
        assert result == [
            str(tmp_path / "a_file.json"),
            str(tmp_path / "b_file.json"),
        ]

    def test_empty_directory_returns_empty_list(self, tmp_path):
        assert discover_corpora(str(tmp_path)) == []


class TestHaversine:
    def test_known_distance_paris_london(self):
        d = haversine(48.8566, 2.3522, 51.5074, -0.1278)
        assert 340 < d < 345

    def test_zero_distance(self):
        d = haversine(48.8566, 2.3522, 48.8566, 2.3522)
        assert d == 0.0

    def test_antipodal(self):
        d = haversine(0.0, 0.0, 0.0, 180.0)
        assert 20000 < d < 20100

    def test_symmetry(self):
        d1 = haversine(48.8566, 2.3522, 51.5074, -0.1278)
        d2 = haversine(51.5074, -0.1278, 48.8566, 2.3522)
        assert abs(d1 - d2) < 0.001


class TestEvaluateGeocoding:
    def test_all_expected_geocoded_country_match(self):
        predictions = [
            {"text": "Paris", "lat": 48.8566, "lon": 2.3522, "country": "FR"},
            {"text": "London", "lat": 51.5074, "lon": -0.1278, "country": "GB"},
        ]
        expected = [
            {"text": "Paris", "country": "FR"},
            {"text": "London", "country": "GB"},
        ]
        result = evaluate_geocoding(predictions, expected)
        assert result["geocoding_rate"] == 1.0
        assert result["country_accuracy"] == 1.0
        assert result["total_expected"] == 2
        assert result["geocoded"] == 2
        assert result["country_matches"] == 2

    def test_partial_geocoding(self):
        predictions = [{"text": "Paris", "lat": 48.8566, "lon": 2.3522, "country": "FR"}]
        expected = [
            {"text": "Paris", "country": "FR"},
            {"text": "Berlin", "country": "DE"},
        ]
        result = evaluate_geocoding(predictions, expected)
        assert result["geocoding_rate"] == 0.5
        assert result["country_accuracy"] == 1.0
        assert result["total_expected"] == 2
        assert result["geocoded"] == 1
        assert result["country_matches"] == 1

    def test_country_mismatch(self):
        predictions = [{"text": "Paris", "lat": 48.8566, "lon": 2.3522, "country": "DE"}]
        expected = [{"text": "Paris", "country": "FR"}]
        result = evaluate_geocoding(predictions, expected)
        assert result["geocoding_rate"] == 1.0
        assert result["country_accuracy"] == 0.0
        assert result["country_matches"] == 0

    def test_no_expected_locations(self):
        result = evaluate_geocoding([{"text": "Paris", "country": "FR"}], [])
        assert result["geocoding_rate"] == 0.0
        assert result["country_accuracy"] == 1.0
        assert result["total_expected"] == 0

    def test_no_predictions(self):
        result = evaluate_geocoding([], [{"text": "Paris", "country": "FR"}])
        assert result["geocoding_rate"] == 0.0
        assert result["country_accuracy"] == 1.0
        assert result["geocoded"] == 0

    def test_both_empty(self):
        result = evaluate_geocoding([], [])
        assert result["geocoding_rate"] == 0.0
        assert result["total_expected"] == 0

    def test_expected_without_country_skips_country_check(self):
        predictions = [{"text": "Paris", "lat": 48.8566, "lon": 2.3522, "country": "FR"}]
        expected = [{"text": "Paris"}]
        result = evaluate_geocoding(predictions, expected)
        assert result["geocoding_rate"] == 1.0
        assert result["country_accuracy"] == 1.0
        assert result["country_matches"] == 0

    def test_distance_metrics_with_coordinates(self):
        predictions = [{"text": "Paris", "lat": 48.8566, "lon": 2.3522, "country": "FR"}]
        expected = [{"text": "Paris", "lat": 48.8566, "lon": 2.3522, "country": "FR"}]
        result = evaluate_geocoding(predictions, expected)
        assert result["mean_distance_km"] == 0.0
        assert result["within_1km"] == 1.0
        assert result["within_10km"] == 1.0
        assert result["within_100km"] == 1.0
        assert result["distance_checkable"] == 1

    def test_distance_metrics_no_lat_lon_in_expected(self):
        predictions = [{"text": "Paris", "lat": 48.8566, "lon": 2.3522, "country": "FR"}]
        expected = [{"text": "Paris", "country": "FR"}]
        result = evaluate_geocoding(predictions, expected)
        assert result["distance_checkable"] == 0
        assert result["mean_distance_km"] == 0.0

    def test_distance_metrics_distant_location(self):
        predictions = [{"text": "Paris", "lat": 48.8566, "lon": 2.3522, "country": "FR"}]
        expected = [{"text": "Paris", "lat": 51.5074, "lon": -0.1278, "country": "GB"}]
        result = evaluate_geocoding(predictions, expected)
        assert 340 < result["mean_distance_km"] < 345
        assert result["within_1km"] == 0.0
        assert result["within_10km"] == 0.0
        assert result["within_100km"] == 0.0

    def test_distance_metrics_partial(self):
        predictions = [
            {"text": "Paris", "lat": 48.8566, "lon": 2.3522, "country": "FR"},
        ]
        expected = [
            {"text": "Paris", "lat": 48.8566, "lon": 2.3522, "country": "FR"},
            {"text": "London", "lat": 51.5074, "lon": -0.1278, "country": "GB"},
        ]
        result = evaluate_geocoding(predictions, expected)
        assert result["distance_checkable"] == 1
        assert result["mean_distance_km"] == 0.0
        assert result["within_1km"] == 1.0

    def test_distance_metrics_empty_expected(self):
        result = evaluate_geocoding(
            [{"text": "Paris", "lat": 48.8566, "lon": 2.3522, "country": "FR"}],
            [],
        )
        assert result["distance_checkable"] == 0
        assert result["mean_distance_km"] == 0.0


class TestEvaluateEventLocation:
    def test_exact_match(self):
        result = evaluate_event_location(
            {"text": "Paris", "country": "FR", "confidence": 0.8},
            {"text": "Paris", "country": "FR"},
        )
        assert result["expected"] is True
        assert result["correct"] is True
        assert result["text_match"] is True
        assert result["country_match"] is True

    def test_text_mismatch(self):
        result = evaluate_event_location(
            {"text": "London", "country": "GB", "confidence": 0.6},
            {"text": "Paris", "country": "FR"},
        )
        assert result["correct"] is False
        assert result["text_match"] is False
        assert result["country_match"] is False

    def test_country_mismatch(self):
        result = evaluate_event_location(
            {"text": "Paris", "country": "DE", "confidence": 0.8},
            {"text": "Paris", "country": "FR"},
        )
        assert result["correct"] is False
        assert result["text_match"] is True
        assert result["country_match"] is False

    def test_no_prediction(self):
        result = evaluate_event_location(None, {"text": "Paris", "country": "FR"})
        assert result["correct"] is False
        assert result["text_match"] is False
        assert result["country_match"] is False

    def test_no_expected(self):
        result = evaluate_event_location(
            {"text": "Paris", "country": "FR", "confidence": 0.8},
            None,
        )
        assert result["expected"] is False
        assert result["correct"] is None

    def test_both_none(self):
        result = evaluate_event_location(None, None)
        assert result["expected"] is False
        assert result["correct"] is None
