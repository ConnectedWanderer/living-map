import type pg from 'pg';
import type { NormalizedArticle } from './normalizer.ts';

const BATCH_SIZE = 100;

/** Batch insert articles with ON CONFLICT deduplication. Returns inserted/skipped counts. */
export async function insertEvents(
  pool: pg.Pool,
  articles: NormalizedArticle[],
): Promise<{ inserted: number; skipped: number }> {
  let inserted = 0;
  let skipped = 0;

  for (let i = 0; i < articles.length; i += BATCH_SIZE) {
    const batch = articles.slice(i, i + BATCH_SIZE);
    const params: unknown[] = [];
    const values: string[] = [];

    for (let j = 0; j < batch.length; j++) {
      const a = batch[j];
      const offset = j * 6;
      values.push(
        `($${offset + 1}, $${offset + 2}, $${offset + 3}, $${offset + 4}, $${offset + 5}, $${offset + 6})`,
      );
      params.push(a.source, a.source_id, a.title, a.description, a.url, a.published_at);
    }

    const result = await pool.query(
      `INSERT INTO events (source, source_id, title, description, url, published_at)
       VALUES ${values.join(', ')}
       ON CONFLICT (source, source_id) DO NOTHING`,
      params,
    );

    inserted += result.rowCount ?? 0;
  }

  skipped = articles.length - inserted;

  return { inserted, skipped };
}
