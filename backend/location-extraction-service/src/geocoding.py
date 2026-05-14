"""Stage 3: Toponym resolution via text2geo offline geocoding."""

from dataclasses import dataclass, field

from text2geo import Geocoder

from src.models import EntityMention, GeocodedLocation


@dataclass
class GeoResult:
    """Result of running Stage 3 (geocoding) of the location extraction pipeline.

    Attributes:
        locations: Geocoded locations as GeocodedLocation records.

    """

    locations: list[GeocodedLocation] = field(default_factory=list)


_geocoder: Geocoder | None = None


def _get_geocoder() -> Geocoder:
    """Get or create the cached text2geo Geocoder instance (dataset='world')."""
    global _geocoder
    if _geocoder is None:
        _geocoder = Geocoder(dataset="world")
    return _geocoder


def _geocode(text: str) -> GeocodedLocation | None:
    """Geocode a single place name via text2geo.

    Args:
        text: Place name to geocode.

    Returns:
        GeocodedLocation with lat, lon, country, or None if unresolvable.

    """
    geo = _get_geocoder()
    result = geo.geocode(text)
    if result:
        return GeocodedLocation(
            lat=result["lat"],
            lon=result["lon"],
            text=text,
            country=result["country"],
        )
    return None


class GeoPipeline:
    """Geocodes NER entity mentions to geographic coordinates via text2geo.

    This is Stage 3 of the location extraction pipeline.  It takes entity
    mentions produced by NerPipeline (stages 1-2) and resolves them to
    lat/lon coordinates, country codes, and canonical names using the
    offline text2geo geocoder with GeoNames data.

    The geocode function is injectable for testing.  By default it uses
    the module-level _geocode backed by a cached text2geo Geocoder.
    """

    def __init__(self, geocode_fn=None):
        """Initialize GeoPipeline.

        Args:
            geocode_fn: Optional callable accepting a place name string
                and returning GeocodedLocation | None.  Defaults to the
                module-level _geocode function backed by text2geo.

        """
        self._geocode_fn = geocode_fn or _geocode

    def run(self, entities: list[EntityMention]) -> GeoResult:
        """Geocode a list of NER entity mentions to geographic coordinates.

        Args:
            entities: EntityMention records with at least 'text' and 'label'.

        Returns:
            GeoResult containing GeocodedLocation records.

        """
        locations = []
        for entity in entities:
            result = self._geocode_fn(entity.text)
            if result is not None:
                locations.append(
                    GeocodedLocation(
                        text=entity.text,
                        lat=result.lat,
                        lon=result.lon,
                        country=result.country,
                        type=entity.label,
                    )
                )
        return GeoResult(locations=locations)
