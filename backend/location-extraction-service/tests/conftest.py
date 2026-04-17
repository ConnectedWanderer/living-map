from unittest.mock import MagicMock

import pytest


@pytest.fixture
def sample_english_text():
    return """
    Breaking news from Paris, France. The city of London has announced new climate policies.
    Floods in the Seine river have caused significant damage. Officials from Berlin and Madrid
    are meeting to discuss the response. The United States has also expressed concern about
    global warming effects.
    """


@pytest.fixture
def sample_french_text():
    return """
    Nouvelles de Paris, France. La ville de Londres a annoncé de nouvelles politiques climatiques.
    Les inondations de la Seine ont causé des dommages importants. Des officiels de Berlin et Madrid
    se réunissent pour discuter de la réponse. Les États-Unis ont également exprimé leur préoccupation
    concernant les effets du réchauffement climatique.
    """


@pytest.fixture
def mixed_english_heavy_text():
    return "Bonjour ! Paris is a beautiful city in France. The Seine river flows through London and downtown."


@pytest.fixture
def mixed_french_heavy_text():
    return "Hello ! La ville de Paris est magnifique le week end. La Seine traverse la France et Londres."


@pytest.fixture
def sample_location_mentions():
    return [
        {"text": "Paris", "label": "GPE", "start": 17, "end": 22},
        {"text": "France", "label": "GPE", "start": 23, "end": 29},
        {"text": "London", "label": "GPE", "start": 50, "end": 56},
        {"text": "Seine", "label": "LOC", "start": 100, "end": 105},
        {"text": "Berlin", "label": "GPE", "start": 150, "end": 156},
        {"text": "Madrid", "label": "GPE", "start": 165, "end": 171},
    ]


@pytest.fixture
def geocoded_locations():
    return [
        {
            "text": "Paris",
            "lat": 48.8566,
            "lon": 2.3522,
            "name": "Paris",
            "country": "FR",
            "type": "GPE",
        },
        {
            "text": "France",
            "lat": 46.2276,
            "lon": 2.2137,
            "name": "France",
            "country": "FR",
            "type": "GPE",
        },
        {
            "text": "London",
            "lat": 51.5074,
            "lon": -0.1278,
            "name": "London",
            "country": "GB",
            "type": "GPE",
        },
        {
            "text": "Seine",
            "lat": 49.0,
            "lon": 2.5,
            "name": "Seine",
            "country": "FR",
            "type": "LOC",
        },
        {
            "text": "Berlin",
            "lat": 52.52,
            "lon": 13.405,
            "name": "Berlin",
            "country": "DE",
            "type": "GPE",
        },
        {
            "text": "Madrid",
            "lat": 40.4168,
            "lon": -3.7038,
            "name": "Madrid",
            "country": "ES",
            "type": "GPE",
        },
    ]


@pytest.fixture
def mock_geocoder():
    """Mock geocoder that returns predictable results."""
    geocoder = MagicMock()
    geocoder.geocode.side_effect = lambda name: {
        "Paris": {"lat": 48.8566, "lon": 2.3522, "name": "Paris", "country": "FR"},
        "France": {"lat": 46.2276, "lon": 2.2137, "name": "France", "country": "FR"},
        "London": {"lat": 51.5074, "lon": -0.1278, "name": "London", "country": "GB"},
        "Seine": {"lat": 49.0, "lon": 2.5, "name": "Seine", "country": "FR"},
        "Berlin": {"lat": 52.52, "lon": 13.405, "name": "Berlin", "country": "DE"},
        "Madrid": {"lat": 40.4168, "lon": -3.7038, "name": "Madrid", "country": "ES"},
    }.get(name)


@pytest.fixture
def expected_event_location():
    return {
        "text": "Paris",
        "lat": 48.8566,
        "lon": 2.3522,
        "country": "FR",
        "country_name": "France",
        "confidence": 0.75,
    }


@pytest.fixture
def expected_output_schema():
    return {
        "detected_language": str,
        "event_location": dict | None,
        "all_locations": list,
        "metadata": {
            "processing_time_ms": int,
            "language_model": str,
            "entities_found": int,
            "entities_geocoded": int,
        },
    }
