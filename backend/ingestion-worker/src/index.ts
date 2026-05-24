import http from 'node:http';
import type cron from 'node-cron';
import pg from 'pg';
import { loadSources } from './config.ts';
import { insertEvents, updateLocation } from './db.ts';
import { extractLocation } from './enrich.ts';
import { createLogger } from './logger.ts';
import { runSource } from './runner.ts';
import { startScheduler } from './scheduler.ts';
import { getAdapter } from './sources/registry.ts';

interface Env {
  PORT?: string;
  DATABASE_URL?: string;
  LOCATION_EXTRACTION_URL?: string;
  LOG_LEVEL?: string;
}

/** Bootstrap the ingestion worker: pool, sources, scheduler, and health server. */
export async function main(
  env: Env,
  deps?: { pool?: pg.Pool; schedule?: typeof cron.schedule },
): Promise<http.Server> {
  const logger = createLogger(env.LOG_LEVEL);
  const pool = deps?.pool ?? new pg.Pool({ connectionString: env.DATABASE_URL });

  const sources = await loadSources(pool);

  const _stop = startScheduler(
    sources,
    (source) =>
      runSource(source, {
        fetch: global.fetch,
        pool,
        fetchArticles: getAdapter(source.type),
        insertEvents,
        updateLocation,
        extractLocation: (text) =>
          extractLocation(text, { url: env.LOCATION_EXTRACTION_URL || '' }),
        locationExtractionUrl: env.LOCATION_EXTRACTION_URL || '',
        logger,
      }),
    deps?.schedule,
  );

  const server = http.createServer((req, res) => {
    if (req.url === '/health' && req.method === 'GET') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ status: 'ok' }));
    } else {
      res.writeHead(404);
      res.end();
    }
  });

  const port = parseInt(env.PORT || '3000', 10);
  logger.info({ port }, 'Server started');
  return server.listen(port);
}
