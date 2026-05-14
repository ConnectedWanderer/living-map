"""Composed pipeline that orchestrates all 4 stages of location extraction."""

import time

from src.disambiguator import DisambiguatePipeline
from src.geocoding import GeoPipeline
from src.models import LocationResult
from src.pipeline import NerPipeline


class LocationPipeline:
    """Composes stages 1-4 of location extraction into a single interface.

    Chains NerPipeline (detection + NER), GeoPipeline (geocoding), and
    DisambiguatePipeline (event location inference) behind one seam.

    Sub-pipelines are injectable for testing (e.g., a mock GeoPipeline
    that doesn't require text2geo GeoNames data).
    """

    def __init__(
        self,
        ner: NerPipeline | None = None,
        geo: GeoPipeline | None = None,
        disambiguator: DisambiguatePipeline | None = None,
    ) -> None:
        self._ner = ner or NerPipeline()
        self._geo = geo or GeoPipeline()
        self._disambiguator = disambiguator or DisambiguatePipeline()

    def run(self, text: str) -> LocationResult:
        """Run all 4 pipeline stages on input text.

        Args:
            text: Raw input text to analyze.

        Returns:
            LocationResult with detected language, event location, all scored
            locations, and processing metadata.

        """
        start = time.monotonic()

        ner_result = self._ner.run(text)
        geo_result = self._geo.run(ner_result.entities)
        dis_result = self._disambiguator.run(geo_result.locations, text)

        elapsed = (time.monotonic() - start) * 1000

        return LocationResult(
            detected_language=ner_result.language,
            model_name=ner_result.model_name,
            event_location=dis_result.event_location,
            all_locations=dis_result.all_locations,
            entities_found=len(ner_result.entities),
            entities_geocoded=len(geo_result.locations),
            processing_time_ms=round(elapsed, 1),
        )
