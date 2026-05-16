"""Typed dataclasses for pipeline intermediate and result records."""

from dataclasses import dataclass


@dataclass
class EntityMention:
    """NER entity mention with text, label, and character offsets."""

    text: str
    label: str
    start: int
    end: int


@dataclass
class GeocodedLocation:
    """Geocoded location with coordinates, country, and optional NER type."""

    text: str
    lat: float
    lon: float
    country: str
    type: str | None = None


@dataclass
class ScoredLocation:
    """Geocoded location with disambiguation score and country name."""

    text: str
    lat: float
    lon: float
    country: str
    country_name: str
    type: str | None = None
    score: float = 0.0


@dataclass
class GeocodeResult:
    """Geocoding details for a successfully geocoded entity."""

    lat: float
    lon: float
    country: str
    country_name: str
    score: float


@dataclass
class EntityResult:
    """Entity mention with optional geocoding result."""

    text: str
    type: str
    start: int
    end: int
    geocoded: bool
    geocoding: GeocodeResult | None = None


@dataclass
class EventLocation:
    """Best-guess event location with confidence score."""

    text: str
    lat: float
    lon: float
    country: str
    country_name: str
    confidence: float


@dataclass
class LocationResult:
    """Full pipeline output with detected language, event location, and metadata."""

    detected_language: str
    model_name: str | None
    event_location: EventLocation | None
    all_entities: list[EntityResult]
    entities_found: int
    entities_geocoded: int
    processing_time_ms: float
