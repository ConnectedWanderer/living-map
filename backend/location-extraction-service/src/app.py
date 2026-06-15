"""Batch job for extracting locations from unprocessed events."""

import os

import psycopg2

from .orchestrator import LocationPipeline


def run_batch(connection, pipeline: LocationPipeline) -> int:
    """Query unprocessed events, run pipeline, update locations in the database.

    Args:
        connection: psycopg2 connection to the database.
        pipeline: LocationPipeline instance for extracting locations.

    Returns:
        Number of events processed (location updated).

    """
    cursor = connection.cursor()
    cursor.execute("SELECT id, title, description FROM events WHERE location IS NULL LIMIT 500")
    rows = cursor.fetchall()

    count = 0
    for event_id, title, description in rows:
        text = f"{title} {description}" if description else title
        result = pipeline.run(text)
        if result.event_location:
            cursor.execute(
                "UPDATE events SET location = ST_SetSRID(ST_MakePoint(%s, %s), 4326), updated_at = now() WHERE id = %s",
                (result.event_location.lon, result.event_location.lat, event_id),
            )
            count += 1

    connection.commit()
    return count


def main(
    database_url: str | None = None, connection=None, pipeline: LocationPipeline | None = None
):
    """Entry point: create connection, run batch, clean up.

    Args:
        database_url: Database connection string. Defaults to DATABASE_URL env var.
        connection: Optional injected connection (for testing). If provided,
            database_url is ignored and caller manages cleanup.
        pipeline: Optional injected pipeline (for testing). Defaults to LocationPipeline().

    """
    if connection is None:
        url = database_url or os.environ["DATABASE_URL"]
        conn = psycopg2.connect(url)
        with conn.cursor() as cur:
            cur.execute("SET search_path TO living_map, public")
        conn.commit()
        own_connection = True
    else:
        conn = connection
        own_connection = False

    pipeline = pipeline or LocationPipeline()

    try:
        run_batch(conn, pipeline)
    finally:
        if own_connection:
            conn.close()
