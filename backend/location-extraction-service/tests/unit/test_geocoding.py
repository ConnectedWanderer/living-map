from unittest.mock import patch

from src.geocoding import GeoPipeline
from src.models import EntityMention, GeocodedLocation


class TestGeoPipeline:
    def test_single_entity_geocoded(self):
        entities = [EntityMention(text="Paris", label="GPE", start=0, end=5)]

        with patch(
            "src.geocoding._geocode",
            return_value=GeocodedLocation(lat=48.8566, lon=2.3522, text="Paris", country="FR"),
        ):
            result = GeoPipeline().run(entities)

        assert len(result.locations) == 1
        loc = result.locations[0]
        assert loc.text == "Paris"
        assert loc.lat == 48.8566
        assert loc.lon == 2.3522
        assert loc.country == "FR"

    def test_multiple_entities_all_geocoded(self):
        entities = [
            EntityMention(text="Paris", label="GPE", start=0, end=5),
            EntityMention(text="London", label="GPE", start=10, end=16),
        ]

        with patch("src.geocoding._geocode") as mock:
            mock.side_effect = [
                GeocodedLocation(lat=48.8566, lon=2.3522, text="Paris", country="FR"),
                GeocodedLocation(lat=51.5074, lon=-0.1278, text="London", country="GB"),
            ]
            result = GeoPipeline().run(entities)

        assert len(result.locations) == 2
        assert result.locations[0].text == "Paris"
        assert result.locations[1].text == "London"

    def test_partial_geocoding(self):
        entities = [
            EntityMention(text="Paris", label="GPE", start=0, end=5),
            EntityMention(text="Atlantis", label="LOC", start=10, end=18),
        ]

        with patch("src.geocoding._geocode") as mock:
            mock.side_effect = [
                GeocodedLocation(lat=48.8566, lon=2.3522, text="Paris", country="FR"),
                None,
            ]
            result = GeoPipeline().run(entities)

        assert len(result.locations) == 1
        assert result.locations[0].text == "Paris"

    def test_no_entities_geocoded(self):
        entities = [EntityMention(text="Atlantis", label="LOC", start=0, end=8)]

        with patch("src.geocoding._geocode", return_value=None):
            result = GeoPipeline().run(entities)

        assert result.locations == []

    def test_empty_input(self):
        result = GeoPipeline().run([])
        assert result.locations == []

    def test_original_text_preserved(self):
        entities = [EntityMention(text="NYC", label="GPE", start=0, end=3)]

        with patch(
            "src.geocoding._geocode",
            return_value=GeocodedLocation(
                lat=40.7128, lon=-74.0060, text="New York City", country="US"
            ),
        ):
            result = GeoPipeline().run(entities)

        assert result.locations[0].text == "NYC"

    def test_no_name_field_in_output(self):
        entities = [EntityMention(text="Paris", label="GPE", start=0, end=5)]

        with patch(
            "src.geocoding._geocode",
            return_value=GeocodedLocation(lat=48.8566, lon=2.3522, text="Paris", country="FR"),
        ):
            result = GeoPipeline().run(entities)

        assert not hasattr(result.locations[0], "name")

    def test_type_preserved_from_entity(self):
        entities = [EntityMention(text="Paris", label="GPE", start=0, end=5)]

        with patch(
            "src.geocoding._geocode",
            return_value=GeocodedLocation(lat=48.8566, lon=2.3522, text="Paris", country="FR"),
        ):
            result = GeoPipeline().run(entities)

        assert result.locations[0].type == "GPE"
