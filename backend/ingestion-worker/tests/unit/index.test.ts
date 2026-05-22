import assert from 'node:assert';
import type http from 'node:http';
import { after, before, describe, it, mock } from 'node:test';
import cron from 'node-cron';
import pg from 'pg';

describe('main', () => {
  let server: http.Server;

  before(async () => {
    const mockPool = () => ({
      query: async () => ({
        rows: [
          {
            id: 1,
            name: 'test-feed',
            type: 'mock-feed',
            config: {},
            schedule: '*/5 * * * *',
          },
        ],
      }),
      end: async () => {},
    });

    mock.method(pg, 'Pool', mockPool);
    mock.method(cron, 'schedule', () => ({ stop: () => {} }));

    const { main } = await import('../../src/index.ts');
    server = await main({
      PORT: '0',
      DATABASE_URL: 'postgres://localhost:5432/test',
      LOG_LEVEL: 'warn',
    });
  });

  after(async () => {
    await new Promise<void>((resolve) => server.close(() => resolve()));
    mock.restoreAll();
  });

  it('responds to GET /health with status ok', async () => {
    const addr = server.address() as import('net').AddressInfo;
    const res = await fetch(`http://localhost:${addr.port}/health`);
    assert.strictEqual(res.status, 200);
    const body = await res.json();
    assert.deepStrictEqual(body, { status: 'ok' });
  });

  it('returns 404 for unknown routes', async () => {
    const addr = server.address() as import('net').AddressInfo;
    const res = await fetch(`http://localhost:${addr.port}/unknown`);
    assert.strictEqual(res.status, 404);
  });
});
