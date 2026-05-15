"""Integration tests for the FastAPI API server endpoints."""

from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.app import app, get_pipeline
from src.models import EntityResult, EventLocation, GeocodeResult, LocationResult


@pytest.fixture
def mock_pipeline():
    pipe = MagicMock()
    pipe.run.return_value = LocationResult(
        detected_language="en",
        model_name="en_core_web_sm",
        event_location=EventLocation(
            text="Paris",
            lat=48.8566,
            lon=2.3522,
            country="FR",
            country_name="France",
            confidence=0.85,
        ),
        all_entities=[
            EntityResult(
                text="Paris",
                type="GPE",
                start=0,
                end=5,
                geocoded=True,
                geocoding=GeocodeResult(
                    lat=48.8566,
                    lon=2.3522,
                    country="FR",
                    country_name="France",
                    score=2.17,
                ),
            ),
            EntityResult(
                text="France",
                type="GPE",
                start=16,
                end=22,
                geocoded=False,
            ),
        ],
        entities_found=2,
        entities_geocoded=1,
        processing_time_ms=150.0,
    )
    return pipe


@pytest.fixture
def client(mock_pipeline):
    app.dependency_overrides[get_pipeline] = lambda: mock_pipeline
    transport = ASGITransport(app=app)
    yield AsyncClient(transport=transport, base_url="http://test")
    app.dependency_overrides.clear()


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_returns_ok(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data == {"status": "ok"}


class TestExtractLocation:
    @pytest.mark.asyncio
    async def test_returns_feature_collection(self, client):
        response = await client.post(
            "/api/extract-location",
            json={"text": "Paris is in France."},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "FeatureCollection"
        assert "features" in data

    @pytest.mark.asyncio
    async def test_feature_contains_event_location(self, client):
        response = await client.post(
            "/api/extract-location",
            json={"text": "Paris is in France."},
        )
        data = response.json()
        features = data["features"]
        assert len(features) == 1
        feature = features[0]
        assert feature["type"] == "Feature"
        assert feature["geometry"] == {
            "type": "Point",
            "coordinates": [2.3522, 48.8566],
        }
        props = feature["properties"]
        assert props["name"] == "Paris"
        assert props["country"] == "FR"
        assert props["country_name"] == "France"
        assert props["confidence"] == 0.85

    @pytest.mark.asyncio
    async def test_geocoding_contains_all_entities(self, client):
        response = await client.post(
            "/api/extract-location",
            json={"text": "Paris is in France."},
        )
        data = response.json()
        geocoding = data["geocoding"]
        assert "all_entities" in geocoding
        all_ent = geocoding["all_entities"]
        assert len(all_ent) == 2

        # Geocoded entity
        paris = all_ent[0]
        assert paris["type"] == "Feature"
        assert paris["geometry"] == {"type": "Point", "coordinates": [2.3522, 48.8566]}
        props = paris["properties"]
        assert props["name"] == "Paris"
        assert props["type"] == "GPE"
        assert props["start"] == 0
        assert props["end"] == 5
        assert props["geocoded"] is True
        assert props["geocoding"]["country"] == "FR"
        assert props["geocoding"]["country_name"] == "France"
        assert props["geocoding"]["score"] == 2.17

        # Non-geocoded entity
        france = all_ent[1]
        assert france["type"] == "Feature"
        assert france["geometry"] is None
        props2 = france["properties"]
        assert props2["name"] == "France"
        assert props2["geocoded"] is False
        assert props2["geocoding"] is None

    @pytest.mark.asyncio
    async def test_geocoding_includes_metadata(self, client):
        response = await client.post(
            "/api/extract-location",
            json={"text": "Paris is in France."},
        )
        data = response.json()
        geocoding = data["geocoding"]
        assert geocoding["query"] == {"text": "Paris is in France."}
        assert geocoding["detected_language"] == "en"
        assert geocoding["model_name"] == "en_core_web_sm"
        assert geocoding["entities_found"] == 2
        assert geocoding["entities_geocoded"] == 1
        assert geocoding["processing_time_ms"] == 150.0

    @pytest.mark.asyncio
    async def test_default_language_is_auto(self, client):
        response = await client.post(
            "/api/extract-location",
            json={"text": "Paris is in France."},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_language_override_accepted(self, client):
        response = await client.post(
            "/api/extract-location",
            json={"text": "Nouvelles de Paris.", "language": "fr"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_empty_text_returns_valid_geojson(self, client, mock_pipeline):
        empty_pipe = MagicMock()
        empty_pipe.run.return_value = LocationResult(
            detected_language="en",
            model_name=None,
            event_location=None,
            all_entities=[],
            entities_found=0,
            entities_geocoded=0,
            processing_time_ms=5.0,
        )
        app.dependency_overrides[get_pipeline] = lambda: empty_pipe
        response = await client.post(
            "/api/extract-location",
            json={"text": ""},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "FeatureCollection"
        assert data["features"] == []
        assert data["geocoding"]["all_entities"] == []
        assert data["geocoding"]["entities_found"] == 0
        assert data["geocoding"]["entities_geocoded"] == 0

    @pytest.mark.asyncio
    async def test_missing_text_returns_422(self, client):
        response = await client.post(
            "/api/extract-location",
            json={},
        )
        assert response.status_code == 422
