import assert from 'node:assert';
import { after, before, beforeEach, describe, it } from 'node:test';
import type pg from 'pg';
import { loadSources } from '../../src/config.ts';
import { cleanTables } from '../helpers.ts';
import { withPostgres } from './setup.ts';

describe('config integration', () => {
  let pool: pg.Pool;
  let stop: () => Promise<void>;

  before(async () => {
    const ctx = await withPostgres();
    pool = ctx.pool;
    stop = ctx.stop;
  });

  after(async () => {
    await stop();
  });

  beforeEach(async () => {
    await cleanTables(pool);
  });

  it('loads enabled sources from the database', async () => {
    await pool.query(
      `INSERT INTO sources (name, type, config, schedule, enabled)
       VALUES ($1, $2, $3, $4, $5)`,
      [
        'integration-test-feed',
        'mock-feed',
        JSON.stringify({ url: 'http://feed', source: 'integration-test' }),
        '*/5 * * * *',
        true,
      ],
    );

    const sources = await loadSources(pool);

    const found = sources.find((s) => s.name === 'integration-test-feed');
    assert.ok(found);
    assert.strictEqual(found.type, 'mock-feed');
    assert.strictEqual(found.schedule, '*/5 * * * *');
    assert.ok(found.config);
  });

  it('excludes disabled sources', async () => {
    await pool.query(
      `INSERT INTO sources (name, type, config, schedule, enabled)
       VALUES ($1, $2, $3, $4, $5)`,
      [
        'integration-test-feed',
        'mock-feed',
        JSON.stringify({ url: 'http://feed', source: 'integration-test' }),
        '*/5 * * * *',
        true,
      ],
    );

    await pool.query(
      `INSERT INTO sources (name, type, config, schedule, enabled)
       VALUES ($1, $2, $3, $4, $5)`,
      ['disabled-feed', 'mock-feed', '{}', '0 * * * *', false],
    );

    const sources = await loadSources(pool);

    const found = sources.find((s) => s.name === 'integration-test-feed');
    assert.ok(found);

    const disabled = sources.find((s) => s.name === 'disabled-feed');
    assert.strictEqual(disabled, undefined);
  });
});
