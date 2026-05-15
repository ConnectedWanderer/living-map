"""FastAPI application for location extraction service."""

import os

import uvicorn
from fastapi import Depends, FastAPI

from .orchestrator import LocationPipeline
from .schemas import (
    EntityFeature,
    EntityFeatureProperties,
    ExtractLocationRequest,
    ExtractLocationResponse,
    GeocodeProperties,
    GeocodingMetadata,
    GeoFeature,
    GeoFeatureProperties,
)

app = FastAPI(title="Location Extraction Service")


def get_pipeline() -> LocationPipeline:
    """Dependency provider for the location extraction pipeline."""
    return LocationPipeline()


@app.get("/health")
async def health():
    """Health check endpoint returning service status."""
    return {"status": "ok"}


def _build_response(result, query_text: str) -> ExtractLocationResponse:
    features = []
    if result.event_location:
        el = result.event_location
        features.append(
            GeoFeature(
                geometry={"type": "Point", "coordinates": [el.lon, el.lat]},
                properties=GeoFeatureProperties(
                    name=el.text,
                    country=el.country,
                    country_name=el.country_name,
                    confidence=el.confidence,
                ),
            )
        )

    all_ent = []
    for ent in result.all_entities:
        geometry = None
        geocoding = None
        if ent.geocoded and ent.geocoding:
            geometry = {"type": "Point", "coordinates": [ent.geocoding.lon, ent.geocoding.lat]}
            geocoding = GeocodeProperties(
                country=ent.geocoding.country,
                country_name=ent.geocoding.country_name,
                score=ent.geocoding.score,
            )

        all_ent.append(
            EntityFeature(
                geometry=geometry,
                properties=EntityFeatureProperties(
                    name=ent.text,
                    type=ent.type,
                    start=ent.start,
                    end=ent.end,
                    geocoded=ent.geocoded,
                    geocoding=geocoding,
                ),
            )
        )

    return ExtractLocationResponse(
        features=features,
        geocoding=GeocodingMetadata(
            query={"text": query_text},
            detected_language=result.detected_language,
            model_name=result.model_name,
            entities_found=result.entities_found,
            entities_geocoded=result.entities_geocoded,
            processing_time_ms=result.processing_time_ms,
            all_entities=all_ent,
        ),
    )


@app.post("/api/extract-location", response_model=ExtractLocationResponse)
async def extract_location(
    request: ExtractLocationRequest,
    pipeline: LocationPipeline = Depends(get_pipeline),
):
    """Extract geographic locations from unstructured text.

    Returns a GeoJSON FeatureCollection with the primary event location
    as the main feature and all scored locations in geocoding metadata.
    """
    result = pipeline.run(request.text)
    return _build_response(result, request.text)


def start():
    """Run the FastAPI server via uvicorn."""
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("src.app:app", host=host, port=port, reload=False)
