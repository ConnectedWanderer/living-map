"""Stage 3: Toponym resolution via text2geo offline geocoding."""

from dataclasses import dataclass, field

from text2geo import Geocoder


@dataclass
class GeoResult:
    """Result of running Stage 3 (geocoding) of the location extraction pipeline.

    Attributes:
        locations: Geocoded location dicts, each with text, lat, lon, country.

    """

    locations: list[dict] = field(default_factory=list)


_geocoder: Geocoder | None = None


def _get_geocoder() -> Geocoder:
    """Get or create the cached text2geo Geocoder instance (dataset='world')."""
    global _geocoder
    if _geocoder is None:
        _geocoder = Geocoder(dataset="world")
    return _geocoder


def _geocode(text: str) -> dict | None:
    """Geocode a single place name via text2geo.

    Args:
        text: Place name to geocode.

    Returns:
        Dict with lat, lon, name, country, or None if unresolvable.

    """
    geo = _get_geocoder()
    result = geo.geocode(text)
    if result:
        return {
            "lat": result["lat"],
            "lon": result["lon"],
            "name": result["name"],
            "country": result["country"],
        }
    return None


class GeoPipeline:
    """Geocodes NER entity mentions to geographic coordinates via text2geo.

    This is Stage 3 of the location extraction pipeline.  It takes entity
    mentions produced by NerPipeline (stages 1-2) and resolves them to
    lat/lon coordinates, country codes, and canonical names using the
    offline text2geo geocoder with GeoNames data.
    """

    def run(self, entities: list[dict]) -> GeoResult:
        """Geocode a list of NER entity mentions to geographic coordinates.

        Args:
            entities: List of entity dicts, each with at least a 'text' key.

        Returns:
            GeoResult containing geocoded locations with text, lat, lon, country.

        """
        locations = []
        for entity in entities:
            result = _geocode(entity["text"])
            if result is not None:
                locations.append(
                    {
                        "text": entity["text"],
                        "lat": result["lat"],
                        "lon": result["lon"],
                        "country": result["country"],
                    }
                )
        return GeoResult(locations=locations)
