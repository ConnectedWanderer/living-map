"""Integration tests for the batch job (run_batch, main)."""

import psycopg2
import pytest
from testcontainers.postgres import PostgresContainer

from src.app import main as batch_main
from src.app import run_batch
from src.models import EventLocation, LocationResult

_EVENTS_TABLE_DDL = """
    CREATE TABLE events (
        id SERIAL PRIMARY KEY,
        source TEXT NOT NULL DEFAULT '',
        source_id TEXT NOT NULL DEFAULT '',
        title TEXT NOT NULL,
        description TEXT,
        url TEXT,
        published_at TIMESTAMPTZ,
        location geometry(Point, 4326),
        location_name TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
"""


class _CannedPipeline:
    def __init__(self, lat=48.8566, lon=2.3522, text="Paris", country="FR", country_name="France"):
        self._lat = lat
        self._lon = lon
        self._text = text
        self._country = country
        self._country_name = country_name

    def run(self, text: str) -> LocationResult:
        return LocationResult(
            detected_language="en",
            model_name="canned",
            event_location=EventLocation(
                text=self._text,
                lat=self._lat,
                lon=self._lon,
                country=self._country,
                country_name=self._country_name,
                confidence=0.85,
            ),
            all_entities=[],
            entities_found=1,
            entities_geocoded=1,
            processing_time_ms=1.0,
        )


def _setup_db(conn):
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    cur.execute("CREATE SCHEMA IF NOT EXISTS living_map")
    cur.execute("SET search_path TO living_map, public")
    cur.execute(_EVENTS_TABLE_DDL)
    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_events_source_source_id
        ON events (source, source_id)
    """)
    conn.autocommit = False


@pytest.fixture(scope="module")
def postgres():
    with PostgresContainer("postgis/postgis:18-3.6-alpine") as container:
        url = container.get_connection_url(driver=None)
        conn = psycopg2.connect(url)
        _setup_db(conn)
        yield conn
        conn.close()


class TestRunBatch:
    def test_handles_no_unprocessed_events(self, postgres):
        conn = postgres
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO events (title, description, source, source_id, location) "
            "VALUES (%s, %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326)) RETURNING id",
            ("Paris is beautiful", "The city of lights", "test", "a0", 2.3522, 48.8566),
        )
        event_id = cur.fetchone()[0]
        conn.commit()

        pipeline = _CannedPipeline()

        count = run_batch(conn, pipeline)

        assert count == 0

        cur.execute(
            "SELECT ST_X(location::geometry), ST_Y(location::geometry) FROM events WHERE id = %s",
            (event_id,),
        )
        lon, lat = cur.fetchone()
        assert abs(lat - 48.8566) < 0.001
        assert abs(lon - 2.3522) < 0.001

    def test_processes_multiple_events(self, postgres):
        conn = postgres
        cur = conn.cursor()
        for i in range(3):
            cur.execute(
                "INSERT INTO events (title, description, source, source_id) VALUES (%s, %s, %s, %s)",
                (f"Event {i}", f"Description {i}", "test", f"b{i}"),
            )
        conn.commit()

        pipeline = _CannedPipeline()

        count = run_batch(conn, pipeline)

        assert count == 3

        cur.execute(
            "SELECT COUNT(*) FROM events WHERE location IS NOT NULL AND source_id LIKE 'b%'",
        )
        assert cur.fetchone()[0] == 3

    def test_processes_one_event(self, postgres):
        conn = postgres
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO events (title, description, source, source_id) VALUES (%s, %s, %s, %s) RETURNING id",
            ("Paris is beautiful", "The city of lights", "test", "a1"),
        )
        event_id = cur.fetchone()[0]
        conn.commit()

        pipeline = _CannedPipeline()

        count = run_batch(conn, pipeline)

        assert count == 1

        cur.execute(
            "SELECT ST_X(location::geometry), ST_Y(location::geometry) FROM events WHERE id = %s",
            (event_id,),
        )
        row = cur.fetchone()
        assert row is not None
        lon, lat = row
        assert abs(lat - 48.8566) < 0.001
        assert abs(lon - 2.3522) < 0.001


class TestMain:
    def test_with_injected_deps(self, postgres):
        conn = postgres
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO events (title, description, source, source_id) VALUES (%s, %s, %s, %s) RETURNING id",
            ("Paris is beautiful", "The city of lights", "test", "c1"),
        )
        event_id = cur.fetchone()[0]
        conn.commit()

        pipeline = _CannedPipeline()

        batch_main(connection=conn, pipeline=pipeline)

        cur.execute(
            "SELECT ST_X(location::geometry), ST_Y(location::geometry) FROM events WHERE id = %s",
            (event_id,),
        )
        row = cur.fetchone()
        assert row is not None
        lon, lat = row
        assert abs(lat - 48.8566) < 0.001
        assert abs(lon - 2.3522) < 0.001

    @pytest.mark.model_dependent
    def test_with_real_pipeline(self, postgres):
        conn = postgres
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO events (title, description, source, source_id) VALUES (%s, %s, %s, %s) RETURNING id",
            (
                "Paris is a beautiful city in France",
                "The Seine river flows through it",
                "test",
                "d1",
            ),
        )
        event_id = cur.fetchone()[0]
        conn.commit()

        from src.orchestrator import LocationPipeline

        pipeline = LocationPipeline()

        batch_main(connection=conn, pipeline=pipeline)

        cur.execute(
            "SELECT location IS NOT NULL FROM events WHERE id = %s",
            (event_id,),
        )
        row = cur.fetchone()
        assert row is not None
        assert row[0] is True

    def test_reads_url_from_env(self, monkeypatch):
        with PostgresContainer("postgis/postgis:18-3.6-alpine") as container:
            url = container.get_connection_url(driver=None)
            conn = psycopg2.connect(url)
            _setup_db(conn)
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO events (title, description, source, source_id) VALUES (%s, %s, %s, %s) RETURNING id",
                ("Paris is beautiful", "The city of lights", "test", "e1"),
            )
            event_id = cur.fetchone()[0]
            conn.commit()
            conn.close()

            monkeypatch.setenv("DATABASE_URL", url)

            pipeline = _CannedPipeline()

            batch_main(pipeline=pipeline)

            conn2 = psycopg2.connect(url)
            cur2 = conn2.cursor()
            cur2.execute("SET search_path TO living_map, public")
            cur2.execute(
                "SELECT ST_X(location::geometry), ST_Y(location::geometry) FROM events WHERE id = %s",
                (event_id,),
            )
            row = cur2.fetchone()
            assert row is not None
            lon, lat = row
            assert abs(lat - 48.8566) < 0.001
            assert abs(lon - 2.3522) < 0.001
            conn2.close()
