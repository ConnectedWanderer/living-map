from src.disambiguator import DisambiguatePipeline
from src.models import GeocodedLocation


class TestDisambiguator:
    def test_empty_locations_returns_none(self):
        result = DisambiguatePipeline().run([], "some text")
        assert result.event_location is None
        assert result.all_locations == []

    def test_single_location_returns_that_location(self):
        locations = [
            GeocodedLocation(text="Paris", lat=48.8566, lon=2.3522, country="FR", type="GPE"),
        ]
        result = DisambiguatePipeline().run(locations, "Event in Paris")
        assert result.event_location is not None
        assert result.event_location.text == "Paris"
        assert result.event_location.lat == 48.8566
        assert result.event_location.lon == 2.3522
        assert result.event_location.country == "FR"
        assert result.event_location.country_name == "France"
        assert 0 <= result.event_location.confidence <= 1

    def test_first_mention_is_primary(self):
        locations = [
            GeocodedLocation(text="London", lat=51.5074, lon=-0.1278, country="GB", type="GPE"),
            GeocodedLocation(text="Paris", lat=48.8566, lon=2.3522, country="FR", type="GPE"),
        ]
        result = DisambiguatePipeline().run(locations, "London and Paris")
        assert result.event_location.text == "London"

    def test_gpe_over_loc_priority(self):
        locations = [
            GeocodedLocation(text="Seine", lat=49.0, lon=2.5, country="FR", type="LOC"),
            GeocodedLocation(text="Paris", lat=48.8566, lon=2.3522, country="FR", type="GPE"),
        ]
        result = DisambiguatePipeline().run(locations, "Along the Seine in Paris")
        assert result.event_location.text == "Paris"

    def test_combined_scoring(self):
        locations = [
            GeocodedLocation(text="London", lat=51.5074, lon=-0.1278, country="GB", type="GPE"),
            GeocodedLocation(text="Seine", lat=49.0, lon=2.5, country="FR", type="LOC"),
            GeocodedLocation(text="Paris", lat=48.8566, lon=2.3522, country="FR", type="GPE"),
        ]
        result = DisambiguatePipeline().run(locations, "London on the Seine and Paris")
        scores = {loc.text: loc.score for loc in result.all_locations}
        assert scores["Seine"] < scores["Paris"]
        assert scores["Paris"] < scores["London"]

    def test_confidence_normalized_to_zero_one(self):
        locations = [
            GeocodedLocation(text="Paris", lat=48.8566, lon=2.3522, country="FR", type="GPE"),
        ]
        result = DisambiguatePipeline().run(locations, "Paris")
        assert result.event_location.confidence == 1.0

        locations2 = [
            GeocodedLocation(text="Seine", lat=49.0, lon=2.5, country="FR", type="LOC"),
        ]
        result2 = DisambiguatePipeline().run(locations2, "Seine")
        assert 0 < result2.event_location.confidence < 1.0

    def test_skips_ungeocoded_locations(self):
        locations = [
            GeocodedLocation(text="Paris", lat=48.8566, lon=2.3522, country="FR", type="GPE"),
        ]
        result = DisambiguatePipeline().run(locations, "Atlantis and Paris")
        assert result.event_location is not None
        assert result.event_location.text == "Paris"
        assert len(result.all_locations) == 1

    def test_country_name_resolution(self):
        locations = [
            GeocodedLocation(text="London", lat=51.5074, lon=-0.1278, country="GB", type="GPE"),
            GeocodedLocation(text="Berlin", lat=52.5200, lon=13.4050, country="DE", type="GPE"),
        ]
        result = DisambiguatePipeline().run(locations, "London and Berlin")
        names = {loc.text: loc.country_name for loc in result.all_locations}
        assert names["London"] == "United Kingdom"
        assert names["Berlin"] == "Germany"
        assert result.event_location.country_name == "United Kingdom"

    def test_context_preposition_boosting(self):
        locations = [
            GeocodedLocation(text="Seine", lat=49.0, lon=2.5, country="FR", type="LOC"),
            GeocodedLocation(text="Paris", lat=48.8566, lon=2.3522, country="FR", type="GPE"),
        ]
        result = DisambiguatePipeline().run(locations, "Flooding in Seine and Paris")
        assert result.event_location.text == "Seine"

        seine_score = next(loc.score for loc in result.all_locations if loc.text == "Seine")
        paris_score = next(loc.score for loc in result.all_locations if loc.text == "Paris")
        assert seine_score > paris_score
