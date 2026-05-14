from unittest.mock import patch

from src.geocoding import GeoPipeline


class TestGeoPipeline:
    """Tests for GeoPipeline — Stage 3 (text2geo geocoding)."""

    def test_single_entity_geocoded(self):
        entities = [
            {"text": "Paris", "label": "GPE", "start": 0, "end": 5},
        ]

        with patch(
            "src.geocoding._geocode",
            return_value={"lat": 48.8566, "lon": 2.3522, "name": "Paris", "country": "FR"},
        ):
            result = GeoPipeline().run(entities)

        assert len(result.locations) == 1
        loc = result.locations[0]
        assert loc["text"] == "Paris"
        assert loc["lat"] == 48.8566
        assert loc["lon"] == 2.3522
        assert loc["country"] == "FR"

    def test_multiple_entities_all_geocoded(self):
        entities = [
            {"text": "Paris", "label": "GPE", "start": 0, "end": 5},
            {"text": "London", "label": "GPE", "start": 10, "end": 16},
        ]

        with patch("src.geocoding._geocode") as mock:
            mock.side_effect = [
                {"lat": 48.8566, "lon": 2.3522, "name": "Paris", "country": "FR"},
                {"lat": 51.5074, "lon": -0.1278, "name": "London", "country": "GB"},
            ]
            result = GeoPipeline().run(entities)

        assert len(result.locations) == 2
        assert result.locations[0]["text"] == "Paris"
        assert result.locations[1]["text"] == "London"

    def test_partial_geocoding(self):
        entities = [
            {"text": "Paris", "label": "GPE", "start": 0, "end": 5},
            {"text": "Atlantis", "label": "LOC", "start": 10, "end": 18},
        ]

        with patch("src.geocoding._geocode") as mock:
            mock.side_effect = [
                {"lat": 48.8566, "lon": 2.3522, "name": "Paris", "country": "FR"},
                None,
            ]
            result = GeoPipeline().run(entities)

        assert len(result.locations) == 1
        assert result.locations[0]["text"] == "Paris"

    def test_no_entities_geocoded(self):
        entities = [
            {"text": "Atlantis", "label": "LOC", "start": 0, "end": 8},
        ]

        with patch("src.geocoding._geocode", return_value=None):
            result = GeoPipeline().run(entities)

        assert result.locations == []

    def test_empty_input(self):
        result = GeoPipeline().run([])
        assert result.locations == []

    def test_original_text_preserved(self):
        entities = [
            {"text": "NYC", "label": "GPE", "start": 0, "end": 3},
        ]

        with patch(
            "src.geocoding._geocode",
            return_value={
                "lat": 40.7128,
                "lon": -74.0060,
                "name": "New York City",
                "country": "US",
            },
        ):
            result = GeoPipeline().run(entities)

        assert result.locations[0]["text"] == "NYC"

    def test_no_name_field_in_output(self):
        entities = [
            {"text": "Paris", "label": "GPE", "start": 0, "end": 5},
        ]

        with patch(
            "src.geocoding._geocode",
            return_value={"lat": 48.8566, "lon": 2.3522, "name": "Paris", "country": "FR"},
        ):
            result = GeoPipeline().run(entities)

        assert "name" not in result.locations[0]

    def test_no_type_field_in_output(self):
        entities = [
            {"text": "Paris", "label": "GPE", "start": 0, "end": 5},
        ]

        with patch(
            "src.geocoding._geocode",
            return_value={"lat": 48.8566, "lon": 2.3522, "name": "Paris", "country": "FR"},
        ):
            result = GeoPipeline().run(entities)

        assert "type" not in result.locations[0]
