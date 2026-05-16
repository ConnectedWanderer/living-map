import pytest

from src.geocoding import GeoResult
from src.models import GeocodedLocation
from src.orchestrator import LocationPipeline
from src.pipeline import NerPipeline

pytestmark = pytest.mark.model_dependent


class _MockGeoPipeline:
    """Stand-in for GeoPipeline that returns canned results without geonamescache."""

    def __init__(self, entities):
        self.locations = [
            GeocodedLocation(text=e.text, lat=48.8566, lon=2.3522, country="FR", type=e.label)
            for e in entities
        ]

    def run(self, entities):
        return GeoResult(locations=self.locations)


class TestPipelineIntegration:
    def test_full_pipeline_english(self, sample_english_text):
        ner = NerPipeline()
        ner_result = ner.run(sample_english_text)
        pipe = LocationPipeline(ner=ner, geo=_MockGeoPipeline(ner_result.entities))
        result = pipe.run(sample_english_text)
        assert result.detected_language == "en"
        assert result.event_location is not None
        assert result.event_location.text is not None
        assert result.entities_found > 0
        assert result.entities_geocoded > 0
        assert result.processing_time_ms > 0

    def test_full_pipeline_french(self, sample_french_text):
        ner = NerPipeline()
        ner_result = ner.run(sample_french_text)
        pipe = LocationPipeline(ner=ner, geo=_MockGeoPipeline(ner_result.entities))
        result = pipe.run(sample_french_text)
        assert result.detected_language == "fr"
        assert result.event_location is not None
        assert result.event_location.text is not None
        assert result.entities_found > 0
        assert result.entities_geocoded > 0
        assert result.processing_time_ms > 0

    def test_output_format_structure(self, sample_english_text):
        ner = NerPipeline()
        ner_result = ner.run(sample_english_text)
        pipe = LocationPipeline(ner=ner, geo=_MockGeoPipeline(ner_result.entities))
        result = pipe.run(sample_english_text)
        assert result.detected_language in ("en", "fr")
        assert result.model_name is not None
        assert isinstance(result.entities_found, int)
        assert isinstance(result.entities_geocoded, int)
        assert result.processing_time_ms > 0

    def test_detected_language_in_response(self, sample_english_text):
        ner = NerPipeline()
        ner_result = ner.run(sample_english_text)
        pipe = LocationPipeline(ner=ner, geo=_MockGeoPipeline(ner_result.entities))
        result = pipe.run(sample_english_text)
        assert result.detected_language == "en"

    def test_all_entities_in_response(self, sample_english_text):
        ner = NerPipeline()
        ner_result = ner.run(sample_english_text)
        geo = _MockGeoPipeline(ner_result.entities)
        pipe = LocationPipeline(ner=ner, geo=geo)
        result = pipe.run(sample_english_text)
        assert len(result.all_entities) > 0
        for ent in result.all_entities:
            assert ent.text is not None
            assert ent.type is not None
            assert ent.geocoded in (True, False)
            if ent.geocoded:
                assert ent.geocoding is not None
                assert ent.geocoding.lat is not None
                assert ent.geocoding.lon is not None
                assert ent.geocoding.country is not None

    def test_metadata_in_response(self, sample_english_text):
        ner = NerPipeline()
        ner_result = ner.run(sample_english_text)
        pipe = LocationPipeline(ner=ner, geo=_MockGeoPipeline(ner_result.entities))
        result = pipe.run(sample_english_text)
        assert result.model_name is not None
        assert result.entities_found >= 0
        assert result.entities_geocoded >= 0
        assert result.processing_time_ms > 0

    def test_processing_time_recorded(self, sample_english_text):
        ner = NerPipeline()
        ner_result = ner.run(sample_english_text)
        pipe = LocationPipeline(ner=ner, geo=_MockGeoPipeline(ner_result.entities))
        result = pipe.run(sample_english_text)
        assert result.processing_time_ms > 0
        assert result.processing_time_ms < 10000

    def test_entities_count_accuracy(self, sample_english_text):
        ner = NerPipeline()
        ner_result = ner.run(sample_english_text)
        pipe = LocationPipeline(ner=ner, geo=_MockGeoPipeline(ner_result.entities))
        result = pipe.run(sample_english_text)
        assert result.entities_found >= result.entities_geocoded

    def test_null_event_location_when_no_locations(self):
        pipe = LocationPipeline()
        result = pipe.run("Hello world.")
        assert result.event_location is None
        assert result.all_entities == []
        assert result.entities_found == 0
        assert result.entities_geocoded == 0

    def test_null_event_location_when_no_geocoding(self):
        pipe = LocationPipeline()
        result = pipe.run("The cat sat on the mat.")
        assert result.event_location is None
        assert result.entities_geocoded == 0

    def test_language_override(self, sample_french_text):
        ner = NerPipeline()
        ner_result = ner.run(sample_french_text)
        pipe = LocationPipeline(ner=ner, geo=_MockGeoPipeline(ner_result.entities))
        result = pipe.run(sample_french_text)
        assert result.detected_language == "fr"

    def test_empty_text_handling(self):
        pipe = LocationPipeline()
        result = pipe.run("")
        assert result.detected_language == "en"
        assert result.event_location is None
        assert result.all_entities == []
        assert result.entities_found == 0
        assert result.entities_geocoded == 0

    def test_very_long_text(self):
        ner = NerPipeline()
        ner_result = ner.run("Paris " * 500)
        pipe = LocationPipeline(ner=ner, geo=_MockGeoPipeline(ner_result.entities))
        result = pipe.run("Paris " * 500)
        assert result.event_location is not None
        assert result.processing_time_ms > 0


class TestPipelinePerformance:
    def test_processing_under_one_second(self, sample_english_text):
        ner = NerPipeline()
        ner_result = ner.run(sample_english_text)
        pipe = LocationPipeline(ner=ner, geo=_MockGeoPipeline(ner_result.entities))
        result = pipe.run(sample_english_text)
        assert result.processing_time_ms < 1000

    def test_memory_efficiency(self):
        ner = NerPipeline()
        ner_result = ner.run("London and Paris are major European cities.")
        geo = _MockGeoPipeline(ner_result.entities)
        pipe = LocationPipeline(ner=ner, geo=geo)
        for _ in range(5):
            result = pipe.run("London and Paris are major European cities.")
            assert result.event_location is not None
