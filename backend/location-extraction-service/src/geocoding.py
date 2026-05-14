"""Stage 3: Toponym resolution via geonamescache offline geocoding."""

from collections import defaultdict
from dataclasses import dataclass, field

import geonamescache

from src.models import EntityMention, GeocodedLocation


@dataclass
class GeoResult:
    """Result of running Stage 3 (geocoding) of the location extraction pipeline.

    Attributes:
        locations: Geocoded locations as GeocodedLocation records.

    """

    locations: list[GeocodedLocation] = field(default_factory=list)


_NAME_INDEX: dict[str, list[dict]] | None = None


def _build_index() -> dict[str, list[dict]]:
    """Build a case-insensitive name-to-cities index from geonamescache."""
    gc = geonamescache.GeonamesCache(min_city_population=500)
    cities = gc.get_cities()
    index: dict[str, list[dict]] = defaultdict(list)
    for city in cities.values():
        name: str = city["name"]
        if name:
            index[name.lower()].append(city)
        alternates: list[str] = city.get("alternatenames") or []
        for alt in alternates:
            if alt:
                index[alt.lower()].append(city)
    return dict(index)


def _get_index() -> dict[str, list[dict]]:
    global _NAME_INDEX
    if _NAME_INDEX is None:
        _NAME_INDEX = _build_index()
    return _NAME_INDEX


def _geocode(text: str) -> GeocodedLocation | None:
    """Geocode a single place name via geonamescache.

    Args:
        text: Place name to geocode.

    Returns:
        GeocodedLocation with lat, lon, country, or None if unresolvable.

    """
    index = _get_index()
    candidates = index.get(text.lower())
    if not candidates:
        return None

    best = max(candidates, key=lambda c: c.get("population") or 0)
    return GeocodedLocation(
        lat=best["latitude"],
        lon=best["longitude"],
        text=text,
        country=best["countrycode"],
    )


class GeoPipeline:
    """Geocodes NER entity mentions to geographic coordinates via geonamescache.

    This is Stage 3 of the location extraction pipeline.  It takes entity
    mentions produced by NerPipeline (stages 1-2) and resolves them to
    lat/lon coordinates, country codes, and canonical names using the
    offline geonamescache with GeoNames data.

    The geocode function is injectable for testing.  By default it uses
    the module-level _geocode backed by a cached geonamescache index.
    """

    def __init__(self, geocode_fn=None):
        """Initialize GeoPipeline.

        Args:
            geocode_fn: Optional callable accepting a place name string
                and returning GeocodedLocation | None.  Defaults to the
                module-level _geocode function backed by geonamescache.

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
