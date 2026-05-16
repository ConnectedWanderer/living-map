"""Pydantic request/response schemas for the location extraction API."""

from pydantic import BaseModel


class ExtractLocationRequest(BaseModel):
    """Request model for location extraction endpoint."""

    text: str
    language: str = "auto"


class GeoFeatureProperties(BaseModel):
    """Properties for the primary event location GeoJSON Feature."""

    name: str
    country: str
    country_name: str
    confidence: float


class GeoFeature(BaseModel):
    """GeoJSON Feature for the primary event location."""

    type: str = "Feature"
    geometry: dict
    properties: GeoFeatureProperties


class GeocodeProperties(BaseModel):
    """Geocoding details for a successfully geocoded entity."""

    country: str
    country_name: str
    score: float


class EntityFeatureProperties(BaseModel):
    """Properties for an entity in all_entities."""

    name: str
    type: str
    start: int
    end: int
    geocoded: bool
    geocoding: GeocodeProperties | None = None


class EntityFeature(BaseModel):
    """GeoJSON Feature for an entity with optional geocoding data."""

    type: str = "Feature"
    geometry: dict | None = None
    properties: EntityFeatureProperties


class GeocodingMetadata(BaseModel):
    """Metadata block containing query info, counts, and all entities."""

    query: dict
    detected_language: str
    model_name: str | None
    entities_found: int
    entities_geocoded: int
    processing_time_ms: float
    all_entities: list[EntityFeature]


class ExtractLocationResponse(BaseModel):
    """GeoJSON FeatureCollection wrapping the primary event location."""

    type: str = "FeatureCollection"
    features: list[GeoFeature]
    geocoding: GeocodingMetadata
