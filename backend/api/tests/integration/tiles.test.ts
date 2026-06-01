import assert from 'node:assert/strict';
import { before, describe, it } from 'node:test';
import type pg from 'pg';
import { withPostgres } from './setup.ts';

describe('tiles integration', () => {
  let pool: pg.Pool;
  let connectionUri: string;

  before(async () => {
    const ctx = await withPostgres();
    pool = ctx.pool;
    connectionUri = ctx.connectionUri;
  });

  it('returns MVT tile for a tile containing seeded events', async () => {
    await pool.query(
      `INSERT INTO events (source, source_id, title, location, location_name, published_at)
       VALUES ('test-source', 'test-1', 'Test Event',
               ST_SetSRID(ST_MakePoint($1, $2), 4326),
               'Paris', now())`,
      [2.35, 48.86],
    );

    process.env.DATABASE_URL = connectionUri;

    const { default: express } = await import('express');
    const { tilesRouter } = await import('../../src/routes/tiles.ts');

    const app = express();
    app.use('/tiles', tilesRouter);

    const server = app.listen(0);
    await new Promise<void>((resolve) => server.on('listening', resolve));
    const addr = server.address() as { port: number };
    const address = `http://localhost:${addr.port}`;

    try {
      const res = await fetch(`${address}/tiles/0/0/0.pbf`);
      assert.equal(res.status, 200);
      assert.equal(res.headers.get('content-type'), 'application/vnd.mapbox-vector-tile');
      const body = await res.arrayBuffer();
      assert.ok(body.byteLength > 0);
    } finally {
      await new Promise<void>((resolve) => server.close(() => resolve()));
    }
  });
});
