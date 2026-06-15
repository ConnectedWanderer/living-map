import pg from 'pg';
import { loadSources } from './config.ts';
import { insertEvents } from './db.ts';
import { createLogger } from './logger.ts';
import { runSource } from './runner.ts';
import { getAdapter } from './sources/registry.ts';

interface Env {
  DATABASE_URL?: string;
  LOG_LEVEL?: string;
}

function runSourceDeps(type: string, pool: pg.Pool, logger: ReturnType<typeof createLogger>) {
  return {
    fetch: global.fetch,
    pool,
    fetchArticles: getAdapter(type),
    insertEvents,
    logger,
  };
}

/** Run all enabled sources once, then exit. */
export async function main(env: Env, deps?: { pool?: pg.Pool }): Promise<void> {
  const logger = createLogger(env.LOG_LEVEL);

  if (!env.DATABASE_URL) {
    throw new Error('DATABASE_URL environment variable is required');
  }

  const pool = deps?.pool ?? new pg.Pool({
    connectionString: env.DATABASE_URL,
    ssl: { rejectUnauthorized: false },
    connectionTimeoutMillis: 5_000,
    idleTimeoutMillis: 30_000,
    max: 10,
  });
  pool.on('error', (err) => {
    logger.error({ err }, 'Unexpected pool error');
  });

  const sources = await loadSources(pool);

  const results = await Promise.allSettled(
    sources.map((source) => runSource(source, runSourceDeps(source.type, pool, logger))),
  );

  for (const result of results) {
    if (result.status === 'rejected') {
      logger.error({ err: result.reason }, 'Source cycle failed');
    }
  }

  if (!deps?.pool) {
    await pool.end();
  }
}

// Start when run directly (not when imported by tests)
if (process.argv[1] && new URL(import.meta.url).pathname === process.argv[1]) {
  await main(process.env as Env);
}
