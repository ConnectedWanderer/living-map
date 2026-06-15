import assert from 'node:assert/strict';
import http from 'node:http';
import { after, afterEach, before, describe, it, mock } from 'node:test';
import express from 'express';
import pg from 'pg';

async function request(
  app: express.Express,
  url: string,
): Promise<{ status: number; headers: http.IncomingHttpHeaders; body: Buffer }> {
  return new Promise((resolve, reject) => {
    const server = app.listen(0, () => {
      const addr = server.address() as { port: number };
      http
        .get(`http://localhost:${addr.port}${url}`, (res) => {
          const chunks: Buffer[] = [];
          res.on('data', (chunk: Buffer) => chunks.push(chunk));
          res.on('end', () => {
            server.close();
            resolve({
              status: res.statusCode ?? 0,
              headers: res.headers,
              body: Buffer.concat(chunks),
            });
          });
        })
        .on('error', (err) => {
          server.close();
          reject(err);
        });
    });
  });
}

describe('routes/tiles', () => {
  let app: express.Express;
  let originalQuery: typeof pg.Pool.prototype.query;
  let originalDbUrl: string | undefined;

  before(async () => {
    originalQuery = pg.Pool.prototype.query;
    originalDbUrl = process.env.DATABASE_URL;
    process.env.DATABASE_URL = 'postgres://user:pass@localhost:5432/testdb';
    app = express();
    const { tilesRouter } = await import('../../src/routes/tiles.ts');
    app.use('/tiles', tilesRouter);
  });

  afterEach(() => {
    mock.restoreAll();
  });

  after(() => {
    pg.Pool.prototype.query = originalQuery;
    if (originalDbUrl === undefined) {
      delete process.env.DATABASE_URL;
    } else {
      process.env.DATABASE_URL = originalDbUrl;
    }
  });

  it('returns 400 when z is not a number', async () => {
    const res = await request(app, '/tiles/abc/15/10.pbf');
    assert.equal(res.status, 400);
  });

  it('returns 400 when z is out of range (0-22)', async () => {
    const res = await request(app, '/tiles/23/0/0.pbf');
    assert.equal(res.status, 400);
  });

  it('returns 400 when x is out of tile range', async () => {
    const res = await request(app, '/tiles/5/32/0.pbf');
    assert.equal(res.status, 400);
  });

  it('returns 400 when y is out of tile range', async () => {
    const res = await request(app, '/tiles/5/0/32.pbf');
    assert.equal(res.status, 400);
  });

  it('returns 204 when getTile returns null (empty tile)', async () => {
    mock.method(pg.Pool.prototype, 'query', () => Promise.resolve({ rows: [] }));
    const res = await request(app, '/tiles/5/15/10.pbf');
    assert.equal(res.status, 204);
  });

  it('returns 200 with MVT buffer when tile has data', async () => {
    mock.method(pg.Pool.prototype, 'query', () =>
      Promise.resolve({ rows: [{ mvt: Buffer.from([1, 2, 3]) }] }),
    );
    const res = await request(app, '/tiles/5/15/10.pbf');
    assert.equal(res.status, 200);
    assert.equal(res.headers['content-type'], 'application/vnd.mapbox-vector-tile');
    assert.deepEqual(res.body, Buffer.from([1, 2, 3]));
  });
});
