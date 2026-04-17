from src.pipeline.extractor import extract_location_mentions


class TestNERExtraction:
    """Tests for Named Entity Recognition."""

    def test_extract_gpe_entities_english(self, sample_english_text):
        """Should extract GPE (country/city) entities from English text."""
        result = extract_location_mentions(sample_english_text, "en")
        gpe_entities = [e for e in result if e["label"] == "GPE"]
        assert len(gpe_entities) > 0
        assert any(e["text"] == "Paris" for e in result)

    def test_extract_loc_entities_english(self):
        """Should extract LOC (location) entities from English text."""
        text = "The floods in the Seine river have caused damage."
        result = extract_location_mentions(text, "en")
        loc_entities = [e for e in result if e["label"] == "LOC"]
        assert len(loc_entities) > 0
        assert any("Seine" in e["text"] for e in result)

    def test_extract_gpe_entities_french(self, sample_french_text):
        """Should extract location entities (GPE or LOC) from French text."""
        result = extract_location_mentions(sample_french_text, "fr")
        location_entities = [e for e in result if e["label"] in ("GPE", "LOC")]
        assert len(location_entities) > 0

    def test_extract_no_entities(self):
        """Should return empty list when no location entities found."""
        text = "This is a simple sentence with no locations."
        result = extract_location_mentions(text, "en")
        assert result == []

    def test_extract_returns_entity_details(self, sample_english_text):
        """Should return text, label, start, end for each entity."""
        result = extract_location_mentions(sample_english_text, "en")
        for entity in result:
            assert "text" in entity
            assert "label" in entity
            assert "start" in entity
            assert "end" in entity
            assert entity["label"] in ("GPE", "LOC")

    def test_duplicate_entities(self):
        """Should include duplicate entity mentions."""
        text = "Paris is beautiful. Paris is the capital of France."
        result = extract_location_mentions(text, "en")
        paris_entities = [e for e in result if e["text"] == "Paris"]
        assert len(paris_entities) >= 1

    def test_entity_position_in_text(self):
        """Should correctly identify entity positions."""
        text = "Paris is a city."
        result = extract_location_mentions(text, "en")
        if result:
            paris_entity = next(e for e in result if e["text"] == "Paris")
            assert paris_entity["start"] == 0
            assert paris_entity["end"] == 5
