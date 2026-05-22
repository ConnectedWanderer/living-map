import type pg from 'pg';
import type { GeoJsonFeatureCollection } from './enrich.ts';
import type { NormalizedArticle } from './normalizer.ts';

/** Batch insert articles with ON CONFLICT deduplication. Returns inserted/skipped counts. */
export async function insertEvents(
  pool: pg.Pool,
  articles: NormalizedArticle[],
): Promise<{ inserted: number; skipped: number }> {
  let inserted = 0;
  let skipped = 0;

  for (const article of articles) {
    const result = await pool.query(
      `INSERT INTO events (source, source_id, title, description, url, published_at)
       VALUES ($1, $2, $3, $4, $5, $6)
       ON CONFLICT (source, source_id) DO NOTHING
       RETURNING id`,
      [
        article.source,
        article.source_id,
        article.title,
        article.description,
        article.url,
        article.published_at,
      ],
    );

    if (result.rowCount && result.rowCount > 0) {
      inserted++;
    } else {
      skipped++;
    }
  }

  return { inserted, skipped };
}

/** Update an event's location column with extracted GeoJSON coordinates. */
export async function updateLocation(
  pool: pg.Pool,
  source: string,
  sourceId: string,
  geoJson: GeoJsonFeatureCollection,
): Promise<void> {
  const feature = geoJson.features[0];
  if (!feature?.geometry?.coordinates) return;

  const [lon, lat] = feature.geometry.coordinates as [number, number];
  await pool.query(
    `UPDATE events SET location = ST_SetSRID(ST_MakePoint($1, $2), 4326), updated_at = now()
     WHERE source = $3 AND source_id = $4`,
    [lon, lat, source, sourceId],
  );
}
