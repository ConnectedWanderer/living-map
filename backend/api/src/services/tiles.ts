import type pg from 'pg';

export async function getTile(
  pool: pg.Pool,
  z: number,
  x: number,
  y: number,
): Promise<Buffer | null> {
  const result = await pool.query(
    `SELECT ST_AsMVT(tile, 'events', 4096, 'mvtgeom') AS mvt
     FROM (
       SELECT
          ST_AsMVTGeom(ST_Transform(location, 3857), ST_TileEnvelope($1, $2, $3), 4096, 256, true) AS mvtgeom,
          id, title, source, published_at, location_name
        FROM events
        WHERE location IS NOT NULL
          AND ST_Transform(location, 3857) && ST_TileEnvelope($1, $2, $3)
     ) AS tile`,
    [z, x, y],
  );

  const row = result.rows[0] as { mvt: Buffer } | undefined;
  if (!row?.mvt || row.mvt.length === 0) {
    return null;
  }
  return row.mvt;
}
