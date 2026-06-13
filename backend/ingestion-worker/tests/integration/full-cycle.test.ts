import assert from 'node:assert';
import { after, before, describe, it } from 'node:test';
import type pg from 'pg';
import { MOCK_FEED_URL } from './helpers.ts';
import { withPostgres } from './setup.ts';

describe('full cycle integration', () => {
  let pool: pg.Pool;
  let stop: () => Promise<void>;

  before(async () => {
    const resp = await fetch(`${MOCK_FEED_URL}/feed?count=1`);
    if (!resp.ok) {
      throw new Error(`Mock feed not healthy at ${MOCK_FEED_URL}`);
    }

    const ctx = await withPostgres();
    pool = ctx.pool;
    stop = ctx.stop;

    await pool.query(
      `INSERT INTO sources (name, type, config, schedule, enabled)
       VALUES ($1, $2, $3::jsonb, $4, true)`,
      [
        'integration-test',
        'mock-feed',
        JSON.stringify({ url: `${MOCK_FEED_URL}/feed?count=2`, source: 'integration-test' }),
        '*/5 * * * *',
      ],
    );
  });

  after(async () => {
    await stop();
  });

  it('main() loads sources, fetches articles, inserts them into DB, and exits', async () => {
    const { main } = await import('../../src/index.ts');

    await main({ LOG_LEVEL: 'warn' }, { pool });

    const result = await pool.query('SELECT COUNT(*) AS count FROM events WHERE source = $1', [
      'integration-test',
    ]);
    assert.strictEqual(Number(result.rows[0].count), 2);
  });
});
