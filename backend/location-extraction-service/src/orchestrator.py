"""Composed pipeline that orchestrates all 4 stages of location extraction."""

import time

from .disambiguator import DisambiguatePipeline, _country_name
from .geocoding import GeoPipeline
from .models import EntityResult, GeocodeResult, LocationResult
from .pipeline import NerPipeline


class LocationPipeline:
    """Composes stages 1-4 of location extraction into a single interface.

    Chains NerPipeline (detection + NER), GeoPipeline (geocoding), and
    DisambiguatePipeline (event location inference) behind one seam.

    Sub-pipelines are injectable for testing (e.g., a mock GeoPipeline
    that doesn't require geonamescache GeoNames data).
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

        all_entities = _build_all_entities(ner_result.entities, geo_result, dis_result)

        return LocationResult(
            detected_language=ner_result.language,
            model_name=ner_result.model_name,
            event_location=dis_result.event_location,
            all_entities=all_entities,
            entities_found=len(ner_result.entities),
            entities_geocoded=len(geo_result.locations),
            processing_time_ms=round(elapsed, 1),
        )


def _build_all_entities(ner_entities, geo_result, dis_result):
    """Merge NER entities with geocoding results into a single ordered list.

    Both geo_result.locations and geo_result.failures preserve the original
    NER entity order.  A cursor over geo_result.locations tracks which NER
    entities were successfully geocoded.
    """
    entities = []
    geo_idx = 0
    for entity in ner_entities:
        if (
            geo_idx < len(geo_result.locations)
            and geo_result.locations[geo_idx].text == entity.text
        ):
            loc = geo_result.locations[geo_idx]
            scored = (
                dis_result.all_locations[geo_idx]
                if geo_idx < len(dis_result.all_locations)
                else None
            )
            entities.append(
                EntityResult(
                    text=entity.text,
                    type=entity.label,
                    start=entity.start,
                    end=entity.end,
                    geocoded=True,
                    geocoding=GeocodeResult(
                        lat=loc.lat,
                        lon=loc.lon,
                        country=loc.country,
                        country_name=scored.country_name if scored else _country_name(loc.country),
                        score=scored.score if scored else 0.0,
                    ),
                )
            )
            geo_idx += 1
        else:
            entities.append(
                EntityResult(
                    text=entity.text,
                    type=entity.label,
                    start=entity.start,
                    end=entity.end,
                    geocoded=False,
                )
            )
    return entities
