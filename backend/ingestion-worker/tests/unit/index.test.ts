import assert from 'node:assert';
import { describe, it } from 'node:test';
import { main } from '../../src/index.ts';

function noopSchedule() {
  return { stop: () => {} };
}

describe('main', () => {
  it('responds to GET /health with status ok', async () => {
    const server = await main(
      { PORT: '0', DATABASE_URL: 'postgres://localhost:5432/test', LOG_LEVEL: 'warn' },
      {
        pool: {
          query: async () => ({
            rows: [
              { id: 1, name: 'test-feed', type: 'mock-feed', config: {}, schedule: '*/5 * * * *' },
            ],
          }),
          end: async () => {},
        } as unknown as import('pg').Pool,
        schedule: noopSchedule as unknown as typeof import('node-cron').schedule,
      },
    );

    const addr = server.address() as import('net').AddressInfo;
    const res = await fetch(`http://localhost:${addr.port}/health`);
    assert.strictEqual(res.status, 200);
    assert.deepStrictEqual(await res.json(), { status: 'ok' });

    await new Promise<void>((resolve) => server.close(() => resolve()));
  });

  it('returns 404 for unknown routes', async () => {
    const server = await main(
      { PORT: '0', DATABASE_URL: 'postgres://localhost:5432/test', LOG_LEVEL: 'warn' },
      {
        pool: {
          query: async () => ({ rows: [] }),
          end: async () => {},
        } as unknown as import('pg').Pool,
        schedule: noopSchedule as unknown as typeof import('node-cron').schedule,
      },
    );

    const addr = server.address() as import('net').AddressInfo;
    const res = await fetch(`http://localhost:${addr.port}/unknown`);
    assert.strictEqual(res.status, 404);

    await new Promise<void>((resolve) => server.close(() => resolve()));
  });
});
