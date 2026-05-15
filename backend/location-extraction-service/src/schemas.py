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


class ScoredFeatureProperties(BaseModel):
    """Properties for a scored location in all_locations."""

    name: str
    country: str
    country_name: str
    type: str | None = None
    score: float


class ScoredFeature(BaseModel):
    """GeoJSON Feature for a scored location with disambiguation score."""

    type: str = "Feature"
    geometry: dict
    properties: ScoredFeatureProperties


class GeocodingMetadata(BaseModel):
    """Metadata block containing query info, counts, and all scored locations."""

    query: dict
    detected_language: str
    model_name: str | None
    entities_found: int
    entities_geocoded: int
    processing_time_ms: float
    all_locations: list[ScoredFeature]


class ExtractLocationResponse(BaseModel):
    """GeoJSON FeatureCollection wrapping the primary event location."""

    type: str = "FeatureCollection"
    features: list[GeoFeature]
    geocoding: GeocodingMetadata
