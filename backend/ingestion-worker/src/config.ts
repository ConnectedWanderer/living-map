import type pg from 'pg';

/** A row from the `sources` table representing an enabled ingestion source. */
export interface SourceRow {
  id: number;
  name: string;
  type: string;
  config: Record<string, unknown>;
  schedule: string;
}

/** Load all enabled sources from PostgreSQL. */
export async function loadSources(pool: pg.Pool): Promise<SourceRow[]> {
  const result = await pool.query<SourceRow>(
    'SELECT id, name, type, config, schedule FROM sources WHERE enabled = true',
  );
  return result.rows;
}
