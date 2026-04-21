class TestDisambiguator:
    """Tests for event location inference (disambiguation)."""

    def test_first_mention_is_primary(self):
        """Earlier mentions should score higher."""
        pass

    def test_gpe_over_loc_priority(self):
        """GPE entities should score higher than LOC."""
        pass

    def test_combined_scoring(self):
        """Should combine position and type scores."""
        pass

    def test_empty_locations_returns_none(self):
        """Should return None for empty location list."""
        pass

    def test_single_location_returns_that_location(self):
        """Should return the only location when list has one item."""
        pass

    def test_confidence_normalized_to_zero_one(self):
        """Confidence score should be between 0 and 1."""
        pass

    def test_return_format_includes_coordinates(self):
        """Should return lat, lon in result."""
        pass

    def test_skips_ungeocoded_locations(self):
        """Should skip locations without coordinates."""
        pass

    def test_context_preposition_boosting(self):
        """Prepositions like 'in', 'at' should boost nearby locations."""
        pass
