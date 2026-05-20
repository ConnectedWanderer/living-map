import type pg from "pg";
import type { NormalizedArticle } from "./normalizer.ts";
import type { GeoJsonFeatureCollection } from "./enrich.ts";

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
      [article.source, article.source_id, article.title, article.description, article.url, article.published_at],
    );

    if (result.rowCount && result.rowCount > 0) {
      inserted++;
    } else {
      skipped++;
    }
  }

  return { inserted, skipped };
}

export async function updateLocation(
  pool: pg.Pool,
  source: string,
  sourceId: string,
  geoJson: GeoJsonFeatureCollection,
): Promise<void> {
  await pool.query(
    `UPDATE events SET location = $1, updated_at = now()
     WHERE source = $2 AND source_id = $3`,
    [JSON.stringify(geoJson), source, sourceId],
  );
}
