import { PostgreSqlContainer } from '@testcontainers/postgresql';
import pg from 'pg';
import { Wait } from 'testcontainers';
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
    .withWaitStrategy(Wait.forListeningPorts())
    .start();

  const connectionUri = container.getConnectionUri() + '?options=-c%20search_path=living_map,public';
  const pool = new pg.Pool({ connectionString: connectionUri });
  pool.on('error', () => {});

  await runMigrations(connectionUri);

  return {
    pool,
    connectionUri,
    stop: async () => {
      await pool.end().catch(() => {});
      await new Promise((r) => setTimeout(r, 100));
    },
  };
}
