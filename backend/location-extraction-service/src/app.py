"""FastAPI application for location extraction service."""

import os

import uvicorn
from fastapi import Depends, FastAPI

from src.orchestrator import LocationPipeline
from src.schemas import (
    ExtractLocationRequest,
    ExtractLocationResponse,
    GeocodingMetadata,
    GeoFeature,
    GeoFeatureProperties,
    ScoredFeature,
    ScoredFeatureProperties,
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

    all_locs = []
    for loc in result.all_locations:
        all_locs.append(
            ScoredFeature(
                geometry={"type": "Point", "coordinates": [loc.lon, loc.lat]},
                properties=ScoredFeatureProperties(
                    name=loc.text,
                    country=loc.country,
                    country_name=loc.country_name,
                    type=loc.type,
                    score=loc.score,
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
            all_locations=all_locs,
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
