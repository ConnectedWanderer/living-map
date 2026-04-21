from src.pipeline.extractor import extract_location_mentions


class TestNERExtraction:
    def test_extract_returns_empty_for_empty_text(self):
        assert extract_location_mentions("", "en") == []

    def test_extract_returns_empty_for_whitespace(self):
        assert extract_location_mentions("   \n\t  ", "en") == []
