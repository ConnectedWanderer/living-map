/**
 * Per-file PostGIS test harness.
 *
 * Each integration test file calls withPostgres() to bring up an ephemeral
 * PostGIS container, run migrations, and return a pool + connection URI.
 * The container and pool are torn down when the test file calls the returned
 * `stop()` function (typically in an after() hook).
 *
 * This keeps every test file fully isolated — no cross-file database state.
 */

import { PostgreSqlContainer } from '@testcontainers/postgresql';
import pg from 'pg';
import { runMigrations } from '../helpers.ts';

export interface PostgresContext {
  pool: pg.Pool;
  connectionUri: string;
  stop: () => Promise<void>;
}

export async function withPostgres(): Promise<PostgresContext> {
  const container = await new PostgreSqlContainer('postgis/postgis:18-3.6-alpine')
    .withDatabase('livingmap_test')
    .withUsername('livingmap')
    .withPassword('livingmap')
    .start();

  const connectionUri = container.getConnectionUri();
  const pool = new pg.Pool({ connectionString: connectionUri });

  await runMigrations(connectionUri);

  return {
    pool,
    connectionUri,
    stop: async () => {
      await pool.end();
      await container.stop();
    },
  };
}
